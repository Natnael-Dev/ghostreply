"""Comprehensive adversarial and lifecycle E2E integration test suite (T4).

Scenarios covered:
1. Happy Path: Inbound WA -> Intake (PROCESS) -> Gate (HOLD) -> Owner Approves -> Send.
2. Adversarial: Replayed approval callback fails idempotency check.
3. Adversarial: Crash during send transition recovers to SEND_UNKNOWN (no silent re-send).
4. Adversarial: Stale message -> Gate rejects with MESSAGE_STALE.
5. Adversarial: Non-owner callback -> Rejection by OwnerGuard.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.approvals.guard import OwnerGuard, UnauthorizedActorError
from app.approvals.repository import DraftRecord, SqliteDraftRepository
from app.approvals.state import DraftState
from app.approvals.tokens import generate_callback_token, hash_callback_token
from app.channels.dispatcher import dispatch_with_rechecks
from app.channels.events import InboundEvent, IntakeVerdict
from app.channels.intake import evaluate_intake_verdict
from app.channels.ledger import SqliteInboundLedger
from app.channels.rate_limiter import SqliteRateLimiter
from app.channels.whatsapp import WhatsAppAdapter
from app.gate.models import GateInput, HoldReasonCode
from app.gate.orchestrator import evaluate_safety_gate
from app.gate.prefilter import Clock


class ControlledClock(Clock):
    """Controllable clock for deterministic E2E temporal testing."""

    def __init__(self, start: datetime) -> None:
        self._current = start

    def now_utc(self) -> datetime:
        return self._current

    def advance(self, seconds: float) -> None:
        self._current += timedelta(seconds=seconds)


def create_inbound_event(
    message_id: str,
    timestamp: datetime,
    body: str = "Hey, are you free today?",
) -> InboundEvent:
    return InboundEvent(
        channel="wa",
        message_id=message_id,
        sender_id="wa:+15550100001",
        chat_id="wa:+15550100001@c.us",
        timestamp=timestamp,
        text=body,
        media_type=None,
        media_id=None,
        is_group=False,
        is_forwarded=False,
        is_quoted=False,
        is_edited=False,
        has_link_preview=False,
        is_bot=False,
        is_self=False,
        raw_metadata={"verified": True},
    )


@pytest.fixture
def e2e_fixtures(tmp_path: Path):
    clock = ControlledClock(datetime(2026, 10, 10, 15, 0, 0, tzinfo=timezone.utc))
    ledger = SqliteInboundLedger(db_path=tmp_path / "ledger.db")
    draft_repo = SqliteDraftRepository(db_path=tmp_path / "drafts.db", clock=clock)
    rate_limiter = SqliteRateLimiter(db_path=tmp_path / "rate.db", clock=clock)
    guard = OwnerGuard(owner_id="owner_123")
    return clock, ledger, draft_repo, rate_limiter, guard


@pytest.mark.anyio
async def test_e2e_scenario_1_happy_path(e2e_fixtures):
    clock, ledger, draft_repo, rate_limiter, guard = e2e_fixtures
    now = clock.now_utc()
    event = create_inbound_event("msg_happy_01", now)

    # 1. Intake Claim & Verdict
    assert await ledger.claim("wa", event.message_id) is True
    assert evaluate_intake_verdict(event) == IntakeVerdict.PROCESS

    # 2. Gate Evaluation (Must Output HOLD)
    gate_inp = GateInput(
        event=event,
        draft_text="Yes, free after 5pm.",
        contact_mode="auto_send",
        retrieved_knowledge=[],
        detected_language="en",
        language_confidence=0.98,
        has_geez_chars=False,
        quoted_claims_verified=True,
        entailment_verified=True,
        entailment_commits_or_agrees=False,
        is_claim_free_allowlisted=None,
        needs_owner=False,
        kill_switch_active=False,
        shadow_mode_active=False,
        rate_limits_clear=True,
    )
    decision = evaluate_safety_gate(gate_inp, clock=clock)
    assert decision.decision == "HOLD"

    # 3. Store Immutable Draft
    token = generate_callback_token()
    draft = DraftRecord(
        draft_id=1,
        channel="wa",
        sender_id=event.sender_id,
        chat_id=event.chat_id,
        inbound_message_id=event.message_id,
        inbound_text=event.text,
        draft_text="Yes, free after 5pm.",
        status=DraftState.HELD,
        token_hash=hash_callback_token(token),
        draft_hash="hash_h1",
        reason_codes=[r.value for r in decision.reason_codes],
        created_at=now,
        updated_at=now,
    )
    await draft_repo.create_held_draft(draft)

    # 4. Owner Approves Callback
    assert guard.verify_actor("owner_123") is True
    transitioned = await draft_repo.transition_state(
        draft.draft_id, DraftState.HELD, DraftState.APPROVED
    )
    assert transitioned is True

    # 5. Outbound Send Dispatch
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"success": true}'
    mock_resp.json.return_value = {"success": True, "id": "wa_out_999"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        adapter = WhatsAppAdapter(
            bridge_url="http://127.0.0.1:3001",
            bridge_token="secret",
        )
        res = await dispatch_with_rechecks(
            draft_id=draft.draft_id,
            chat_id=draft.chat_id,
            text=draft.draft_text,
            adapter=adapter,
            draft_repo=draft_repo,
            rate_limiter=rate_limiter,
        )
        assert res.status == "SENT"
        assert res.channel_message_id == "wa_out_999"
        mock_post.assert_awaited_once()

    updated = await draft_repo.get_draft(draft.draft_id)
    assert updated.status == DraftState.SENT


@pytest.mark.anyio
async def test_e2e_scenario_2_replayed_approval_callback(e2e_fixtures):
    clock, _, draft_repo, _, guard = e2e_fixtures
    now = clock.now_utc()
    token = generate_callback_token()
    draft = DraftRecord(
        draft_id=2,
        channel="wa",
        sender_id="wa:1",
        chat_id="wa:1@c.us",
        inbound_message_id="msg_replay_02",
        inbound_text="Hi",
        draft_text="Hello",
        status=DraftState.HELD,
        token_hash=hash_callback_token(token),
        draft_hash="hash_h2",
        reason_codes=[],
        created_at=now,
        updated_at=now,
    )
    await draft_repo.create_held_draft(draft)

    assert guard.verify_actor("owner_123") is True
    assert (
        await draft_repo.transition_state(2, DraftState.HELD, DraftState.APPROVED)
        is True
    )

    dup_transition = await draft_repo.transition_state(
        2, DraftState.HELD, DraftState.APPROVED
    )
    assert dup_transition is False


@pytest.mark.anyio
async def test_e2e_scenario_3_crash_during_send_moves_to_send_unknown(e2e_fixtures):
    clock, _, draft_repo, rate_limiter, _ = e2e_fixtures
    now = clock.now_utc()
    draft = DraftRecord(
        draft_id=3,
        channel="wa",
        sender_id="wa:2",
        chat_id="wa:2@c.us",
        inbound_message_id="msg_crash_03",
        inbound_text="Status?",
        draft_text="Working on it",
        status=DraftState.APPROVED,
        token_hash="thash3",
        draft_hash="dhash3",
        reason_codes=[],
        created_at=now,
        updated_at=now,
    )
    await draft_repo.create_held_draft(draft)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = ConnectionResetError("Remote bridge severed")
        adapter = WhatsAppAdapter(
            bridge_url="http://127.0.0.1:3001",
            bridge_token="secret",
        )
        res = await dispatch_with_rechecks(
            draft_id=3,
            chat_id=draft.chat_id,
            text=draft.draft_text,
            adapter=adapter,
            draft_repo=draft_repo,
            rate_limiter=rate_limiter,
        )
        assert res.status == "SEND_UNKNOWN"
        assert "Remote bridge severed" in (res.error or "")

    updated = await draft_repo.get_draft(3)
    assert updated.status == DraftState.SEND_UNKNOWN


@pytest.mark.anyio
async def test_e2e_scenario_4_stale_message_rejected(e2e_fixtures):
    clock, ledger, _, _, _ = e2e_fixtures
    now = clock.now_utc()
    stale_event = create_inbound_event(
        "msg_stale_04", now - timedelta(minutes=15)
    )

    assert await ledger.claim("wa", stale_event.message_id) is True

    gate_inp = GateInput(
        event=stale_event,
        draft_text="Quick response",
        contact_mode="auto_send",
        retrieved_knowledge=[],
        detected_language="en",
        language_confidence=0.99,
        has_geez_chars=False,
        quoted_claims_verified=True,
        entailment_verified=True,
        entailment_commits_or_agrees=False,
        is_claim_free_allowlisted=None,
        needs_owner=False,
        kill_switch_active=False,
        shadow_mode_active=False,
        rate_limits_clear=True,
    )
    decision = evaluate_safety_gate(gate_inp, clock=clock)
    assert decision.decision == "HOLD"
    assert HoldReasonCode.MESSAGE_STALE in decision.reason_codes


@pytest.mark.anyio
async def test_e2e_scenario_5_unauthorized_actor_rejected(e2e_fixtures):
    _, _, _, _, guard = e2e_fixtures

    with pytest.raises(UnauthorizedActorError) as exc_info:
        guard.verify_actor("attacker_999")

    assert "Actor attacker_999 is not authorized" in str(exc_info.value)
