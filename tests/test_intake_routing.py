import pytest
from datetime import datetime, timezone
from pathlib import Path

from app.channels.events import InboundEvent, IntakeVerdict
from app.channels.intake import IntakeRouter, evaluate_intake_verdict
from app.channels.ledger import SqliteInboundLedger


def make_event(
    is_group: bool = False,
    is_bot: bool = False,
    is_self: bool = False,
    message_id: str = "msg_1",
) -> InboundEvent:
    return InboundEvent(
        channel="wa",
        message_id=message_id,
        sender_id="wa:+15550100000",
        chat_id="wa:+15550100000@c.us",
        timestamp=datetime.now(timezone.utc),
        text="Hello agent",
        media_type=None,
        media_id=None,
        is_group=is_group,
        is_forwarded=False,
        is_quoted=False,
        is_edited=False,
        has_link_preview=False,
        is_bot=is_bot,
        is_self=is_self,
    )


def test_pure_verdict_valid_user():
    event = make_event()
    assert evaluate_intake_verdict(event) == IntakeVerdict.PROCESS


@pytest.mark.parametrize("is_group,is_bot,is_self", [
    (True, False, False),   # Group chat
    (False, True, False),   # Automated bot
    (False, False, True),   # Self message from owner
    (True, True, False),    # Bot in a group
    (True, False, True),    # Self in a group
    (False, True, True),    # Self bot
    (True, True, True),     # All triage triggers active
])
def test_pure_verdict_drops_adversarial_and_non_direct(
    is_group, is_bot, is_self
):
    event = make_event(is_group=is_group, is_bot=is_bot, is_self=is_self)
    assert evaluate_intake_verdict(event) == IntakeVerdict.DROP


@pytest.mark.anyio
async def test_intake_router_with_idempotency_ledger(tmp_path: Path):
    db_file = tmp_path / "test_intake.db"
    ledger = SqliteInboundLedger(db_path=db_file)
    router = IntakeRouter(ledger=ledger)

    event = make_event(message_id="msg_atomic_1")

    # First arrival: legitimate 1-on-1 -> PROCESS
    v1 = await router.intake(event)
    assert v1 == IntakeVerdict.PROCESS

    # Duplicate arrival: duplicate replay -> DROP
    v2 = await router.intake(event)
    assert v2 == IntakeVerdict.DROP


@pytest.mark.anyio
async def test_intake_router_drops_group_without_claiming_ledger(
    tmp_path: Path
):
    db_file = tmp_path / "test_intake_drop.db"
    ledger = SqliteInboundLedger(db_path=db_file)
    router = IntakeRouter(ledger=ledger)

    group_event = make_event(is_group=True, message_id="msg_group_1")
    verdict = await router.intake(group_event)
    assert verdict == IntakeVerdict.DROP

    # Ensure ledger was not polluted by dropped messages
    assert await ledger.claim("wa", "msg_group_1") is True
