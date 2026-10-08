"""Atomic idempotency ledger for incoming channel messages."""
import sqlite3
import time
from pathlib import Path
from typing import Literal, Protocol

ChannelType = Literal["wa", "tg"]
DEFAULT_DB_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "assistant.db"
)


class InboundLedger(Protocol):
    """Atomic ledger ensuring exactly-once processing per channel message."""

    async def claim(self, channel: ChannelType, message_id: str) -> bool:
        """Atomically insert (channel, message_id).

        Returns True if newly claimed, False if already processed or in-flight.
        """
        ...


class SqliteInboundLedger:
    """SQLite implementation of InboundLedger using a unique constraint."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inbound_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    claimed_at REAL NOT NULL,
                    UNIQUE(channel, message_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_inbound_ledger_lookup
                ON inbound_ledger(channel, message_id)
            """)

    async def claim(self, channel: ChannelType, message_id: str) -> bool:
        """Atomically attempt to claim a message.

        Returns True on successful insert, False on duplicate key constraint.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = (
                    "INSERT INTO inbound_ledger "
                    "(channel, message_id, claimed_at) VALUES (?, ?, ?)"
                )
                conn.execute(query, (channel, message_id, time.time()))
                return True
        except sqlite3.IntegrityError:
            return False
