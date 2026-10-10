"""Adversarial and behavioral tests for send-time rechecks and idempotency (T3)."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import pytest

from app.approvals.repository import DraftRecord, SqliteDraftRepository
from app.approvals.state import DraftState
from app.channels.base import ChannelAdapter, ContactProfile, SendResult
from app.channels.dispatcher import DispatchResult, dispatch_with_rechecks
from app.channels.events import InboundEvent
from app.channels.rate_limiter import SqliteRateLimiter


class MockChannelAdapter(ChannelAdapter):
    channel_name = "wa"

    def __init__(self, should_crash: bool = False, success: bool = True) -> None:
        self.should_crash = should_crash
        self.success = success
        self.sent_messages: list[tuple[str, str]] = []

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def send_text(self, recipient_id: str, text: str) -> SendResult:
        if self.should_crash:
            raise ConnectionResetError("Socket severed during transmission")
        if not self.success:
            return SendResult(
                success=False,
                channel_message_id=None,
                error_message="Gateway error",
            )
        self.sent_messages.append((recipient_id, text))
        return SendResult(
            success=True,
            channel_message_id="msg_out_123",
            sent_at=datetime.now(timezone.utc),
        )

    async def get_contact_info(self, contact_id: str) -> ContactProfile:
        return ContactProfile(contact_id=contact_id, display_name="Test", handle_or_phone=None)

    async def download_media(self, media_id: str) -> bytes:
        return b""

    def register_inbound_handler(self, handler) -> None:
        pass

    def stream_inbound(self):
        pass


@pytest.fixture
async def setup_env(tmp_path: Path):
    repo = SqliteDraftRepository(db_path=tmp_path / "drafts.db")
    limiter = SqliteRateLimiter(
        db_path=tmp_path / "rate.db",
        cooldown_seconds=60.0,
        global_cap=10,
    )
    draft = DraftRecord(
        draft_id=1,
        channel="wa",
        sender_id="wa:+15550100000",
        chat_id="wa:+15550100000@c.us",
        inbound_message_id="msg_in_01",
        inbound_text="Free?",
        draft_text="Free at 5.",
        status=DraftState.APPROVED,
        token_hash="thash",
        draft_hash="dhash",
        reason_codes=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repo.create_held_draft(draft)
    return repo, limiter, draft


@pytest.mark.anyio
async def test_kill_switch_aborts_send_and_reverts_to_held(setup_env):
    repo, limiter, draft = setup_env
    adapter = MockChannelAdapter()

    res = await dispatch_with_rechecks(
        draft_id=draft.draft_id,
        chat_id=draft.chat_id,
        text=draft.draft_text,
        adapter=adapter,
        draft_repo=repo,
        rate_limiter=limiter,
        kill_switch_active=True,
        shadow_mode=False,
    )

    assert res.status == "ABORTED"
    assert res.reason == "KILL_SWITCH_ENGAGED"
    assert len(adapter.sent_messages) == 0

    updated = await repo.get_draft(draft.draft_id)
    assert updated.status == DraftState.HELD


@pytest.mark.anyio
async def test_shadow_mode_suppresses_send_and_logs(setup_env):
    repo, limiter, draft = setup_env
    adapter = MockChannelAdapter()

    res = await dispatch_with_rechecks(
        draft_id=draft.draft_id,
        chat_id=draft.chat_id,
        text=draft.draft_text,
        adapter=adapter,
        draft_repo=repo,
        rate_limiter=limiter,
        kill_switch_active=False,
        shadow_mode=True,
    )

    assert res.status == "SHADOW_LOGGED"
    assert len(adapter.sent_messages) == 0

    updated = await repo.get_draft(draft.draft_id)
    assert updated.status == DraftState.SHADOW_LOGGED


@pytest.mark.anyio
async def test_rate_limit_exceeded_aborts_and_reverts_to_held(setup_env):
    repo, limiter, draft = setup_env
    adapter = MockChannelAdapter()

    await limiter.record_send(draft.chat_id)

    res = await dispatch_with_rechecks(
        draft_id=draft.draft_id,
        chat_id=draft.chat_id,
        text=draft.draft_text,
        adapter=adapter,
        draft_repo=repo,
        rate_limiter=limiter,
        kill_switch_active=False,
        shadow_mode=False,
    )

    assert res.status == "ABORTED"
    assert res.reason == "RATE_LIMIT_EXCEEDED"
    assert len(adapter.sent_messages) == 0

    updated = await repo.get_draft(draft.draft_id)
    assert updated.status == DraftState.HELD


@pytest.mark.anyio
async def test_happy_path_send_and_transitions_to_sent(setup_env):
    repo, limiter, draft = setup_env
    adapter = MockChannelAdapter()

    res = await dispatch_with_rechecks(
        draft_id=draft.draft_id,
        chat_id=draft.chat_id,
        text=draft.draft_text,
        adapter=adapter,
        draft_repo=repo,
        rate_limiter=limiter,
        kill_switch_active=False,
        shadow_mode=False,
    )

    assert res.status == "SENT"
    assert len(adapter.sent_messages) == 1
    assert adapter.sent_messages[0] == (draft.chat_id, draft.draft_text)

    updated = await repo.get_draft(draft.draft_id)
    assert updated.status == DraftState.SENT


@pytest.mark.anyio
async def test_crash_during_send_moves_to_send_unknown(setup_env):
    repo, limiter, draft = setup_env
    adapter = MockChannelAdapter(should_crash=True)

    res = await dispatch_with_rechecks(
        draft_id=draft.draft_id,
        chat_id=draft.chat_id,
        text=draft.draft_text,
        adapter=adapter,
        draft_repo=repo,
        rate_limiter=limiter,
        kill_switch_active=False,
        shadow_mode=False,
    )

    assert res.status == "SEND_UNKNOWN"
    assert "Socket severed" in (res.error or "")

    updated = await repo.get_draft(draft.draft_id)
    assert updated.status == DraftState.SEND_UNKNOWN
