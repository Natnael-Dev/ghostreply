"""Rate limiting protocol and SQLite-backed implementation (Phase 6)."""
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Optional, Protocol

from app.gate.prefilter import Clock, SystemClock

DEFAULT_RATE_DB_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "rate_limits.db"
)


class RateLimiter(Protocol):
    """Protocol governing per-chat cooldowns and global rate caps."""

    async def check_limits(self, chat_id: str) -> bool:
        """Return True if send rate is within per-chat and global allowances."""
        ...

    async def record_send(self, chat_id: str) -> None:
        """Increment counters and reset per-chat cooldown."""
        ...


class SqliteRateLimiter:
    """Stateful SQLite-backed rate limiter with injectable clock."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        clock: Optional[Clock] = None,
        cooldown_seconds: float = 60.0,
        global_cap: int = 30,
        global_window_seconds: float = 3600.0,
    ) -> None:
        self.db_path = db_path or DEFAULT_RATE_DB_PATH
        self.clock = clock or SystemClock()
        self.cooldown_seconds = cooldown_seconds
        self.global_cap = global_cap
        self.global_window_seconds = global_window_seconds
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS send_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    sent_at REAL NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_send_chat ON send_log(chat_id, sent_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_send_time ON send_log(sent_at)"
            )

    async def check_limits(self, chat_id: str) -> bool:
        """Check if send is permitted under cooldown and global cap."""
        now = self.clock.now_utc().timestamp()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT MAX(sent_at) FROM send_log WHERE chat_id = ?",
                (chat_id,),
            )
            row = cur.fetchone()
            if row and row[0] is not None:
                last_sent = float(row[0])
                if (now - last_sent) < self.cooldown_seconds:
                    return False

            window_start = now - self.global_window_seconds
            cur = conn.execute(
                "SELECT COUNT(*) FROM send_log WHERE sent_at >= ?",
                (window_start,),
            )
            count = cur.fetchone()[0]
            if count >= self.global_cap:
                return False

        return True

    async def record_send(self, chat_id: str) -> None:
        """Record outbound message send timestamp."""
        now = self.clock.now_utc().timestamp()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO send_log (chat_id, sent_at) VALUES (?, ?)",
                (chat_id, now),
            )
