"""Pure state machine and repository contracts governing draft lifecycle."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal, Optional, Protocol

from app.contracts.events import ChannelType

DraftOrigin = Literal["ai", "owner_manual"]


class DraftState(str, Enum):
    """Lifecycle states of a draft reply."""

    HELD = "HELD"
    APPROVED = "APPROVED"
    SENDING = "SENDING"
    SENT = "SENT"
    REJECTED = "REJECTED"
    EDITED = "EDITED"
    EXPIRED = "EXPIRED"
    SHADOW_LOGGED = "SHADOW_LOGGED"
    SEND_UNKNOWN = "SEND_UNKNOWN"


class InvalidTransitionError(ValueError):
    """Raised when an illegal draft state transition is attempted."""


VALID_TRANSITIONS: dict[DraftState, set[DraftState]] = {
    DraftState.HELD: {
        DraftState.APPROVED,
        DraftState.REJECTED,
        DraftState.EDITED,
        DraftState.EXPIRED,
    },
    DraftState.APPROVED: {
        DraftState.SENDING,
        DraftState.SHADOW_LOGGED,
        DraftState.HELD,
    },
    DraftState.SENDING: {
        DraftState.SENT,
        DraftState.SEND_UNKNOWN,
        DraftState.HELD,
    },
    # Terminal states
    DraftState.SENT: set(),
    DraftState.REJECTED: set(),
    DraftState.EDITED: set(),
    DraftState.EXPIRED: set(),
    DraftState.SHADOW_LOGGED: set(),
    DraftState.SEND_UNKNOWN: set(),
}


def validate_transition(current: DraftState, target: DraftState, created_at: Optional[datetime] = None) -> bool:
    """Validate whether transitioning from current to target is allowed."""
    allowed = VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition draft from {current.value} to {target.value}"
        )
    return True


@dataclass(frozen=True)
class DraftRecord:
    """Immutable representation of a held reply draft."""

    draft_id: int
    channel: ChannelType
    sender_id: str
    chat_id: str
    inbound_message_id: str
    inbound_text: Optional[str]
    draft_text: str
    status: DraftState
    token_hash: str
    draft_hash: str
    reason_codes: list[str]
    created_at: datetime
    updated_at: datetime


class DraftRepository(Protocol):
    """Abstract interface for draft storage and state transitions."""

    async def get_draft(self, draft_id: int) -> Optional[DraftRecord]:
        ...

    async def create_held_draft(self, draft: DraftRecord) -> int:
        ...

    async def transition_state(
        self, draft_id: int, expected_state: DraftState, new_state: DraftState
    ) -> bool:
        ...
