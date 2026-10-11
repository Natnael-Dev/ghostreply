"""Time abstractions for deterministic testing and timeouts."""
from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    """Injectable time provider for deterministic testing."""

    def now_utc(self) -> datetime:
        ...


class SystemClock:
    """Standard system clock returning UTC datetime."""

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)
