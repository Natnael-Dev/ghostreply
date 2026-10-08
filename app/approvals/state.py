"""Pure state machine governing human-in-the-loop draft lifecycle."""
from enum import Enum


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


def validate_transition(current: DraftState, target: DraftState) -> bool:
    """Validate whether transitioning from current to target is allowed."""
    allowed = VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition draft from {current.value} to {target.value}"
        )
    return True
