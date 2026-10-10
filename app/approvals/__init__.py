"""Approvals core and draft lifecycle package."""
from app.approvals.guard import OwnerGuard, UnauthorizedActorError
from app.approvals.legacy import router
from app.approvals.repository import DraftRecord, SqliteDraftRepository
from app.approvals.state import (
    DraftState,
    InvalidTransitionError,
    validate_transition,
)
from app.approvals.tokens import (
    create_scoped_action_token,
    generate_callback_token,
    hash_callback_token,
    parse_scoped_action_token,
    verify_callback_token,
)

__all__ = [
    "DraftRecord",
    "DraftState",
    "InvalidTransitionError",
    "OwnerGuard",
    "SqliteDraftRepository",
    "UnauthorizedActorError",
    "create_scoped_action_token",
    "generate_callback_token",
    "hash_callback_token",
    "parse_scoped_action_token",
    "router",
    "validate_transition",
    "verify_callback_token",
]
