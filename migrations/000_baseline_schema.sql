-- Baseline SQLite schema for GhostReply
-- Initial schema baseline

CREATE TABLE IF NOT EXISTS held (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL,
    chat_id TEXT,
    incoming TEXT,
    reply TEXT,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL,
    kind TEXT,
    target TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL,
    chat_id TEXT,
    role TEXT,
    content TEXT
);

CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages (chat_id, id);

CREATE TABLE IF NOT EXISTS contact_modes (
    name TEXT PRIMARY KEY,
    mode TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS message_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL,
    chat_id TEXT,
    name TEXT,
    direction TEXT,
    body TEXT,
    outcome TEXT
);

CREATE INDEX IF NOT EXISTS idx_message_log_ts ON message_log (ts);
