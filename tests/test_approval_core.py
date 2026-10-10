import pytest
from datetime import datetime, timezone
from pathlib import Path

from app.approvals.state import (
    DraftState,
    validate_transition,
    InvalidTransitionError,
)
from app.approvals.tokens import (
    generate_callback_token,
    hash_callback_token,
    verify_callback_token,
    create_scoped_action_token,
    parse_scoped_action_token,
)
from app.approvals.guard import OwnerGuard, UnauthorizedActorError
from app.approvals.repository import DraftRecord, SqliteDraftRepository


def test_draft_state_transitions():
    # Valid transitions
    assert validate_transition(DraftState.HELD, DraftState.APPROVED) is True
    assert validate_transition(DraftState.APPROVED, DraftState.SENDING) is True
    assert validate_transition(DraftState.SENDING, DraftState.SENT) is True
    assert validate_transition(DraftState.HELD, DraftState.REJECTED) is True

    # Invalid: HELD directly to SENT without APPROVED
    with pytest.raises(InvalidTransitionError):
        validate_transition(DraftState.HELD, DraftState.SENT)

    # Invalid: Terminal states cannot transition
    with pytest.raises(InvalidTransitionError):
        validate_transition(DraftState.SENT, DraftState.HELD)

    with pytest.raises(InvalidTransitionError):
        validate_transition(DraftState.REJECTED, DraftState.APPROVED)


def test_callback_token_generation_and_constant_time_verification():
    token = generate_callback_token()
    assert len(token) >= 8

    token_hash = hash_callback_token(token)
    assert len(token_hash) == 64  # SHA-256 hex length

    # Successful verification
    assert verify_callback_token(token, token_hash) is True

    # Tampered token fails
    assert verify_callback_token("wrong_token_123", token_hash) is False

    # Scoped action serialization
    scoped = create_scoped_action_token("a", 1042, token)
    action, draft_id, parsed_tok = parse_scoped_action_token(scoped)
    assert action == "a"
    assert draft_id == 1042
    assert parsed_tok == token


def test_owner_guard_rejects_unauthorized_actors():
    guard = OwnerGuard(owner_id="owner_12345")
    # Allowed
    assert guard.verify_actor("owner_12345") is True

    # Rejected wrong owner
    with pytest.raises(UnauthorizedActorError):
        guard.verify_actor("stranger_99999")


@pytest.mark.anyio
async def test_draft_repository_immutability_and_state(tmp_path: Path):
    db_file = tmp_path / "test_approvals.db"
    repo = SqliteDraftRepository(db_path=db_file)

    token = generate_callback_token()
    token_hash = hash_callback_token(token)

    draft = DraftRecord(
        draft_id=1,
        channel="wa",
        sender_id="wa:+15550100000",
        chat_id="wa:+15550100000@c.us",
        inbound_message_id="msg_001",
        inbound_text="Are you free?",
        draft_text="Yes, free at 4pm.",
        status=DraftState.HELD,
        token_hash=token_hash,
        draft_hash="hash_draft_123",
        reason_codes=["CONTACT_MODE_ASK_OR_IGNORE"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    created_id = await repo.create_held_draft(draft)
    assert created_id == 1

    fetched = await repo.get_draft(1)
    assert fetched is not None
    assert fetched.draft_text == "Yes, free at 4pm."
    assert fetched.status == DraftState.HELD

    # Transition state to APPROVED
    success = await repo.transition_state(
        1, DraftState.HELD, DraftState.APPROVED
    )
    assert success is True

    # Replayed token or wrong expected state fails
    dup_transition = await repo.transition_state(
        1, DraftState.HELD, DraftState.APPROVED
    )
    assert dup_transition is False
