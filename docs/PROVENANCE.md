# GhostReply Codebase Provenance

**Document Status:** Fact-Checked Baseline Audit  
**Audit Date:** 2026-10-10  
**Target Repository:** `ghostreply` (`7fbfb78492686282724e6838c087679cbdb3dc6a`)

---

## 1. Upstream Source Repository

- **Source URL:** `https://github.com/Shahd132/Whatsapp-Assistant-Agent.git`
- **Initial Baseline Commit:** `29a36920253457a4192ddbbf61c33f2a74c76b91` ("import baseline from the original whatsapp repo")
- **Upstream License:** `null` (The upstream repository contains no license file, and the GitHub API returns `license: null`).
- **Legal Status:** The licensing question is open. In the absence of an upstream open-source license grant, code provenance must be strictly tracked, and imported components must be cleanly decoupled or replaced.

---

## 2. Baseline Import Inventory

Commit `29a3692` imported 42 files from the upstream prototype repository. An analysis comparing commit `29a3692` to `HEAD` reveals the current line-level similarity and state of all 42 files:

### 2.1 Unmodified Files (31 files verbatim identical to imported version)
1. `app/dashboard.html` (100% similarity)
2. `app/knowledge_base/about_me.txt` (100% similarity)
3. `app/knowledge_base/ai_prompt_instructions.txt` (100% similarity)
4. `app/knowledge_base/my_schedule.txt` (100% similarity)
5. `app/knowledge_base/personal_facts.txt` (100% similarity)
6. `app/knowledge_base/services_and_prices.txt` (100% similarity)
7. `whatsapp-bridge/.gitignore` (100% similarity)
8. `whatsapp-bridge/auth_info_baileys/.keep` (100% similarity)
9. `whatsapp-bridge/bridge_api.js` (100% similarity)
10. `whatsapp-bridge/check_session.js` (100% similarity)
11. `whatsapp-bridge/clean_auth.js` (100% similarity)
12. `whatsapp-bridge/config.js` (100% similarity)
13. `whatsapp-bridge/delete_session.js` (100% similarity)
14. `whatsapp-bridge/direct_baileys.js` (100% similarity)
15. `whatsapp-bridge/direct_test.js` (100% similarity)
16. `whatsapp-bridge/index.js` (100% similarity)
17. `whatsapp-bridge/package.json` (100% similarity)
18. `whatsapp-bridge/package-lock.json` (100% similarity)
19. `whatsapp-bridge/pair.js` (100% similarity)
20. `whatsapp-bridge/patch_baileys.js` (100% similarity)
21. `whatsapp-bridge/qr.js` (100% similarity)
22. `whatsapp-bridge/session_manager.js` (100% similarity)
23. `whatsapp-bridge/status.js` (100% similarity)
24. `whatsapp-bridge/test_client.js` (100% similarity)
25. `whatsapp-bridge/test_connection.js` (100% similarity)
26. `whatsapp-bridge/test_integration.js` (100% similarity)
27. `whatsapp-bridge/test_webhook.js` (100% similarity)
28. `whatsapp-bridge/test.js` (100% similarity)
29. `whatsapp-bridge/test2.js` (100% similarity)
30. `whatsapp-bridge/update_session.js` (100% similarity)
31. `whatsapp-bridge/verify_session.js` (100% similarity)

### 2.2 Modified Files (10 files refactored or hardened since import)
1. `app/assistant.py` (partially modified with tool schema updates)
2. `app/config.py` (heavily modified: validation, pydantic, fail-closed settings)
3. `app/contacts.py` (modified: extraction and typing)
4. `app/dashboard.py` (heavily modified: authentication and routes)
5. `app/db.py` (heavily modified: audit triggers, fail-closed defaults)
6. `app/llm.py` (heavily modified: schema parsing and structured output)
7. `app/main.py` (heavily modified: FastAPI routing, health checks, bridge lifecycles)
8. `app/tts.py` (refactored behind service abstraction)
9. `app/whatsapp.py` (refactored into transport adapter)
10. `requirements.txt` (modified: dependencies pinned, cryptography added)

### 2.3 Deleted Files (1 file removed)
1. `app/exporter.py` (removed and replaced with `app/export/` parsers)

---

## 3. Sanitization Actions Prior to Baseline Import

Before committing `29a3692` to the repository history, the owner conducted an initial sanitization pass:
1. Stripped personal telephone numbers and contact identifiers from prototype test files.
2. Removed runtime logging artifacts, database dumps (`.sqlite`), and session tokens.
3. Removed hardcoded API keys from configuration files.

Subsequent sanitization and security audits in Phase 6.6 confirmed that all remaining sensitive defaults have been set to fail-closed (`auto_reply="0"`, `direct_send="0"`, `contact_mode="hold"`).
