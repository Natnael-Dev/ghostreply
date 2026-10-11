"""Database migration runner with backups and forward-only tracking."""
import logging
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def create_backup(db_path: Path) -> Path | None:
    """Create a timestamped backup before migrations if database file exists and is non-empty."""
    if not db_path.exists() or db_path.stat().st_size == 0:
        return None

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    backup_path = db_path.with_name(f"{db_path.name}.{timestamp}.bak")
    shutil.copy2(db_path, backup_path)
    return backup_path


def init_migration_table(conn: sqlite3.Connection) -> None:
    """Ensure schema_migrations tracking table exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at REAL NOT NULL
        )
    """)


def get_applied_migrations(conn: sqlite3.Connection) -> set[str]:
    """Return set of migration version names already applied."""
    init_migration_table(conn)
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {r[0] for r in rows}


import re

ALTER_COLUMN_PATTERN = re.compile(
    r"^\s*ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)\s+",
    re.IGNORECASE,
)


def _strip_comments(sql: str) -> str:
    """Remove SQL block and line comments."""
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    lines = [re.sub(r"--.*$", "", line) for line in sql.splitlines()]
    return "\n".join(lines).strip()


def _split_statements(sql: str) -> list[str]:
    """Split SQL script into complete statements using sqlite3.complete_statement."""
    statements: list[str] = []
    buf: list[str] = []
    for line in sql.splitlines(keepends=True):
        buf.append(line)
        candidate = "".join(buf)
        if sqlite3.complete_statement(candidate):
            stmt = candidate.strip()
            if stmt:
                statements.append(stmt)
            buf = []
    rem = "".join(buf).strip()
    if rem:
        statements.append(rem)
    return statements


def _apply_migration_sql(conn: sqlite3.Connection, sql_content: str) -> None:
    statements = _split_statements(sql_content)
    for stmt in statements:
        cleaned = _strip_comments(stmt)
        if not cleaned:
            continue
        match = ALTER_COLUMN_PATTERN.match(cleaned)
        if match:
            table, column = match.group(1), match.group(2)
            existing_cols = {
                r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            if column in existing_cols:
                continue
        conn.execute(stmt)


def run_migrations(db_path: Path, migrations_dir: Path | None = None) -> list[str]:
    """Apply all pending SQL migrations forward-only in lexical order.
    
    Creates a timestamped backup before applying any new migrations.
    Returns list of newly applied migration names.
    """
    target_dir = migrations_dir or MIGRATIONS_DIR
    if not target_dir.exists():
        return []

    migration_files = sorted(target_dir.glob("*.sql"))
    if not migration_files:
        return []

    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Check which migrations are pending first
    conn = sqlite3.connect(db_path)
    try:
        applied = get_applied_migrations(conn)
        pending = [f for f in migration_files if f.name not in applied]
    finally:
        conn.close()

    if not pending:
        return []

    # Create backup before applying changes
    create_backup(db_path)

    newly_applied = []
    conn = sqlite3.connect(db_path)
    try:
        for sql_file in pending:
            sql_content = sql_file.read_text(encoding="utf-8")
            with conn:
                _apply_migration_sql(conn, sql_content)
                now_ts = datetime.now(timezone.utc).timestamp()
                conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (sql_file.name, now_ts),
                )
            newly_applied.append(sql_file.name)
    finally:
        conn.close()

    return newly_applied
