# Operator Runbook

This document details day-to-day operations, emergency controls, recovery procedures, and troubleshooting for `ghostreply`.

---

## 1. Start-Up Commands

### 1. Python FastAPI Backend
Start the main application service on `127.0.0.1:8000`:
```bash
uvicorn app.main:app --port 8000
```

### 2. WhatsApp Node.js Bridge
Start the WhatsApp Web Puppeteer bridge on port `3001`:
```bash
cd whatsapp-bridge
node index.js
```

---

## 2. Emergency Controls & Kill Switches

### Accurate Kill Switch Behavior (v0.1)
- **Legacy Inbound Webhook**: In `app/main.py:91-92`, when `auto_reply` is disabled (`db.auto_reply_enabled() == False`), incoming messages that would otherwise be replied to are intercepted and held with reason `"paused"`.
- **Dashboard Direct Send**: In `app/assistant.py:160`, `db.direct_send_enabled()` controls whether the owner's instructions to Mika in the dashboard send directly or display a confirmation card.
- **Outbound Dispatcher Parameter**: `dispatch_with_rechecks()` in `app/channels/dispatcher.py:30` defines a `kill_switch_active` parameter, but **this is NOT wired into the live execution path until Phase 7.1**.

### Engaging Emergency Kill Switch
To clamp all automated processing and direct sending via database settings:
```bash
python -c "from app import db; db.set_setting('auto_reply', '0'); db.set_setting('direct_send', '0')"
```
Or via the Dashboard controls toggle (`/api/controls/auto-reply`, `/api/controls/direct-send`).

---

## 3. Environment Variables

The table below lists all environment variables detected across `app/` and `whatsapp-bridge/`:

| Variable | Default | Purpose / Source Location |
|---|---|---|
| `ALLOWED_CONTACTS` | `""` | Comma-separated whitelist of allowed phone numbers (`app/main.py:36`, `whatsapp-bridge/index.js:23`). |
| `BRIDGE_API_TOKEN` | `""` | Shared secret header `x-bridge-token` for bridge-to-app auth (`app/approvals/legacy.py:51`, `app/dashboard.py:174`, `app/main.py:67`, `whatsapp-bridge/bridge_api.js:27`). |
| `BRIDGE_API_URL` | `http://127.0.0.1:3001` | URL of local WhatsApp bridge (`app/approvals/legacy.py:46`, `app/channels/whatsapp.py:28`, `app/dashboard.py:168`). |
| `BRIDGE_API_PORT` | `3001` | Listening port for the bridge API (`whatsapp-bridge/bridge_api.js:28`). |
| `BACKEND_URL` | `http://localhost:8000/webhook` | Webhook URL where the bridge posts incoming messages (`whatsapp-bridge/index.js:21`). |
| `ALLOW_GROUPS` | `false` | Whether to process group chats (`app/main.py:32`, `whatsapp-bridge/index.js:22`). |
| `REPLY_WITH_VOICE` | `false` | Whether auto-replies synthesize voice notes (`app/main.py:31`). |
| `DASHBOARD_PASSWORD` / `DASHBOARD_TOKEN` | `""` | Authentication token/password for the web dashboard (`app/dashboard.py:68`). |
| `TRUST_PROXY` | `false` | Trust reverse proxy headers for rate limiting (`app/dashboard.py:54`). |
| `DASHBOARD_WHISPER_SIZE` | `None` | Whisper model size override for dashboard audio (`app/dashboard.py:273`). |
| `WHISPER_MODEL_SIZE` | `small` | Default model size for speech-to-text (`app/stt.py:14`). |
| `OPENAI_API_KEY` | *(required for LLM)* | API key for OpenAI client (`app/llm.py:44`). |
| `OPENAI_MODEL` | `None` (SDK default) | LLM model override (`app/assistant.py:143`, `app/llm.py:243`). |
| `ASSISTANT_NAME` | `Mika` | Name used for the AI companion (`app/assistant.py:27`). |
| `USER_NAME` | `the owner` | Owner name referenced in prompts (`app/llm.py:38`). |
| `APP_LOG_FILE` | `data/app.log` | Destination path for application event logs (`app/log.py:32`). |
| `MESSAGE_RETENTION_DAYS` | `30` | Retention window for message history before purging (`app/db.py:196`). |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-base` | Sentence transformer embedding model (`app/style_retrieval.py:21`). |
| `STYLE_RETRIEVAL` | `true` | Enable/disable past style example retrieval (`app/style_retrieval.py:41`). |
| `TTS_PROVIDER` | `edge` | TTS engine provider (`edge` or `openai`) (`app/tts.py:56`). |
| `DASHBOARD_VOICE_AR` | `ar-EG-SalmaNeural` | Arabic voice for Edge TTS (`app/tts.py:26`). |
| `DASHBOARD_VOICE_EN` | `en-US-JennyNeural` | English voice for Edge TTS (`app/tts.py:27`). |
| `OPENAI_TTS_MODEL` | `gpt-4o-mini-tts` | Model for OpenAI TTS (`app/tts.py:46`). |
| `OPENAI_TTS_VOICE` | `coral` | Voice for OpenAI TTS (`app/tts.py:47`). |
| `OPENAI_TTS_STYLE` | *(prompt string)* | Voice instructions for OpenAI TTS (`app/tts.py:49`). |
| `PUPPETEER_EXECUTABLE_PATH`| `None` (bundled Chromium) | Custom browser executable path for Puppeteer (`whatsapp-bridge/index.js:61`). |
| `HF_HUB_DOWNLOAD_TIMEOUT` | `120` | Timeout for Hugging Face model downloads (`app/download_blip.py:3`). |

---

## 4. Database Maintenance & Backups

- **Automatic Backups**:
  Any migration execution creates an atomic timestamped backup (`data/assistant.db.<timestamp>.bak`) prior to altering the schema.
- **Manual Backup**:
  ```bash
  cp data/assistant.db data/assistant.db.manual.bak
  ```
- **Integrity Check**:
  ```bash
  sqlite3 data/assistant.db "PRAGMA integrity_check;"
  ```

---

## 5. Secret Vault Operations

- The session vault (`app/session_vault.py`) encrypts credentials and tokens at rest.
- **Key Derivation**: `hashlib.scrypt` ($N=16384, r=8, p=1$) + AES-256-GCM.
- Unlocked secrets reside strictly in process memory and are never serialized or logged.
- Failed unlock attempts engage a 15-minute lockout after 5 consecutive failures.
