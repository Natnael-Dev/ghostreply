"""Immutable draft repository and storage contracts."""
import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.approvals.state import DraftState, validate_transition
from app.channels.events import ChannelType

DEFAULT_DB_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "assistant.db"
)


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


class SqliteDraftRepository:
    """SQLite-backed immutable repository for held drafts."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS held_queue (
                    draft_id INTEGER PRIMARY KEY,
                    channel TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    inbound_message_id TEXT NOT NULL,
                    inbound_text TEXT,
                    draft_text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    draft_hash TEXT NOT NULL,
                    reason_codes TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    UNIQUE(channel, inbound_message_id)
                )
            """)

    async def create_held_draft(self, draft: DraftRecord) -> int:
        """Atomically insert an immutable held draft record."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO held_queue (
                    draft_id, channel, sender_id, chat_id,
                    inbound_message_id, inbound_text, draft_text,
                    status, token_hash, draft_hash, reason_codes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft.draft_id,
                    draft.channel,
                    draft.sender_id,
                    draft.chat_id,
                    draft.inbound_message_id,
                    draft.inbound_text,
                    draft.draft_text,
                    draft.status.value,
                    draft.token_hash,
                    draft.draft_hash,
                    json.dumps(draft.reason_codes),
                    draft.created_at.timestamp(),
                    draft.updated_at.timestamp(),
                ),
            )
            return cur.lastrowid or draft.draft_id

    async def get_draft(self, draft_id: int) -> Optional[DraftRecord]:
        """Fetch draft by draft_id."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM held_queue WHERE draft_id = ?",
                (draft_id,),
            ).fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    async def transition_state(
        self,
        draft_id: int,
        expected_state: DraftState,
        new_state: DraftState,
    ) -> bool:
        """Atomically transition status from expected_state to new_state."""
        validate_transition(expected_state, new_state)
        now_ts = time.time()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                UPDATE held_queue
                SET status = ?, updated_at = ?
                WHERE draft_id = ? AND status = ?
                """,
                (new_state.value, now_ts, draft_id, expected_state.value),
            )
            return cur.rowcount > 0

    def _row_to_record(self, row: sqlite3.Row) -> DraftRecord:
        return DraftRecord(
            draft_id=row["draft_id"],
            channel=row["channel"],
            sender_id=row["sender_id"],
            chat_id=row["chat_id"],
            inbound_message_id=row["inbound_message_id"],
            inbound_text=row["inbound_text"],
            draft_text=row["draft_text"],
            status=DraftState(row["status"]),
            token_hash=row["token_hash"],
            draft_hash=row["draft_hash"],
            reason_codes=json.loads(row["reason_codes"]),
            created_at=datetime.fromtimestamp(
                row["created_at"], tz=timezone.utc
            ),
            updated_at=datetime.fromtimestamp(
                row["updated_at"], tz=timezone.utc
            ),
        )
