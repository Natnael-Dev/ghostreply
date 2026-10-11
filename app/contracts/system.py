"""System-level protocols for rate limiting and idempotency ledgers."""
from typing import Protocol

from app.contracts.events import ChannelType


class RateLimiter(Protocol):
    """Protocol governing per-chat cooldowns and global rate caps."""

    async def check_limits(self, chat_id: str) -> bool:
        """Return True if send rate is within per-chat and global allowances."""
        ...

    async def record_send(self, chat_id: str) -> None:
        """Increment counters and reset per-chat cooldown."""
        ...


class InboundLedger(Protocol):
    """Atomic ledger ensuring exactly-once processing per channel message."""

    async def claim(self, channel: ChannelType, message_id: str) -> bool:
        """Atomically insert (channel, message_id).

        Returns True if newly claimed, False if already processed or in-flight.
        """
        ...
