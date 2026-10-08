-- Migration 001: Inbound Ledger
-- Enforces atomic idempotency for incoming channel messages.

CREATE TABLE IF NOT EXISTS inbound_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    message_id TEXT NOT NULL,
    claimed_at REAL NOT NULL,
    UNIQUE(channel, message_id)
);

CREATE INDEX IF NOT EXISTS idx_inbound_ledger_lookup
ON inbound_ledger(channel, message_id);
