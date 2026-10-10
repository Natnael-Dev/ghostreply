from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Optional

if TYPE_CHECKING:
    from app.approvals.repository import SqliteDraftRepository

from app.approvals.state import DraftState
from app.channels.base import ChannelAdapter
from app.channels.rate_limiter import RateLimiter


@dataclass(frozen=True)
class DispatchResult:
    """Outcome of an outbound dispatch attempt with send-time rechecks."""

    status: Literal["SENT", "ABORTED", "SHADOW_LOGGED", "SEND_UNKNOWN"]
    reason: Optional[str] = None
    error: Optional[str] = None
    channel_message_id: Optional[str] = None


async def dispatch_with_rechecks(
    draft_id: int,
    chat_id: str,
    text: str,
    adapter: ChannelAdapter,
    draft_repo: SqliteDraftRepository,
    rate_limiter: Optional[RateLimiter] = None,
    kill_switch_active: bool = False,
    shadow_mode: bool = False,
) -> DispatchResult:
    """Execute final pre-flight checks and atomic send transitions."""
    # 1. Kill Switch Re-verification
    if kill_switch_active:
        await draft_repo.transition_state(
            draft_id, DraftState.APPROVED, DraftState.HELD
        )
        return DispatchResult(status="ABORTED", reason="KILL_SWITCH_ENGAGED")

    # 2. Shadow Mode Re-verification
    if shadow_mode:
        await draft_repo.transition_state(
            draft_id, DraftState.APPROVED, DraftState.SHADOW_LOGGED
        )
        return DispatchResult(status="SHADOW_LOGGED", reason="SHADOW_MODE_ENABLED")

    # 3. Rate Limit & Cooldown Re-verification
    if rate_limiter and not await rate_limiter.check_limits(chat_id):
        await draft_repo.transition_state(
            draft_id, DraftState.APPROVED, DraftState.HELD
        )
        return DispatchResult(status="ABORTED", reason="RATE_LIMIT_EXCEEDED")

    # 4. Atomic Transition to SENDING
    if not await draft_repo.transition_state(
        draft_id, DraftState.APPROVED, DraftState.SENDING
    ):
        return DispatchResult(
            status="ABORTED", reason="INVALID_TRANSITION_OR_CONFLICT"
        )

    # 5. Socket Transmission with Crash Isolation
    return await _execute_transmission(
        draft_id, chat_id, text, adapter, draft_repo, rate_limiter
    )


async def _execute_transmission(
    draft_id: int,
    chat_id: str,
    text: str,
    adapter: ChannelAdapter,
    draft_repo: SqliteDraftRepository,
    rate_limiter: Optional[RateLimiter],
) -> DispatchResult:
    try:
        res = await adapter.send_text(chat_id, text)
        if res.success:
            await draft_repo.transition_state(
                draft_id, DraftState.SENDING, DraftState.SENT
            )
            if rate_limiter:
                await rate_limiter.record_send(chat_id)
            return DispatchResult(
                status="SENT", channel_message_id=res.channel_message_id
            )
        await draft_repo.transition_state(
            draft_id, DraftState.SENDING, DraftState.SEND_UNKNOWN
        )
        return DispatchResult(status="SEND_UNKNOWN", error=res.error_message)
    except Exception as exc:
        await draft_repo.transition_state(
            draft_id, DraftState.SENDING, DraftState.SEND_UNKNOWN
        )
        return DispatchResult(status="SEND_UNKNOWN", error=str(exc))
