# Operator Runbook

This document details day-to-day operations, emergency controls, recovery procedures, and troubleshooting for `ghostreply`.

---

## 1. Emergency Controls (Kill Switches)

### Global Kill Switch
If unexpected behavior occurs, engage the global kill switch immediately:
```bash
# Disable all automated processing and direct sending
python -c "from app import db; db.set_setting('auto_reply', '0'); db.set_setting('direct_send', '0')"
```
Or via the Dashboard settings toggle.

### Process Termination
To stop all background services immediately:
- Terminate the Python FastAPI process (`uvicorn app.main:app`).
- Stop the WhatsApp bridge Node process (`node index.js`).

---

## 2. Environment Setup & Configuration

1. Copy example configuration:
   ```bash
   cp .env.example .env
   ```
2. Configure mandatory parameters:
   - `DASHBOARD_PASSWORD`: Strong master passphrase for UI access.
   - `OPENAI_API_KEY`: API credential for agent completions.
   - `BRIDGE_SECRET`: Shared secret for WhatsApp Node bridge communication.
3. Database initialization:
   ```bash
   python -c "from app import db; db.init()"
   ```
   This automatically runs all pending forward migrations in `migrations/` and verifies audit triggers.

---

## 3. Database Maintenance & Backups

- **Automatic Backups**:
  Any invocation of `run_migrations()` creates an atomic backup (`data/assistant.db.<timestamp>.bak`) prior to altering the schema.
- **Manual Backup**:
  ```bash
  cp data/assistant.db data/assistant.db.manual.bak
  ```
- **Integrity Check**:
  ```bash
  sqlite3 data/assistant.db "PRAGMA integrity_check;"
  ```

---

## 4. Secret Vault Operations

- The session vault (`app/security/vault.py`) protects Telegram MTProto session strings and cryptographic keys.
- **Unlock Vault**: Vaults require password-derived key derivation at boot.
- Keys are kept strictly in-memory and are never written to disk or logs.
- If a session is corrupted, re-authenticate via the interactive Telethon prompt.

---

## 5. Troubleshooting & Diagnostics

- **Run Test Suite**:
  ```bash
  python -m pytest -v
  ```
- **Check Audit Log**:
  ```bash
  sqlite3 data/assistant.db "SELECT id, datetime(ts, 'unixepoch'), kind, target FROM audit ORDER BY id DESC LIMIT 20;"
  ```
- **Check Pending Held Drafts**:
  ```bash
  sqlite3 data/assistant.db "SELECT id, datetime(ts, 'unixepoch'), chat_id, status FROM held WHERE status = 'pending';"
  ```
