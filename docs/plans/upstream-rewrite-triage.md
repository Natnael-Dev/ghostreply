# Upstream Rewrite Triage and Decoupling Plan

## 1. Raw Baseline Inventory: `git diff-tree --no-commit-id --name-only -r 29a3692`
The 42 files imported from the upstream baseline at commit `29a3692`:
```text
app/__init__.py
app/agent_graph.py
app/approvals.py
app/assistant.py
app/contacts.py
app/controls.py
app/dashboard.html
app/dashboard.py
app/db.py
app/download_blip.py
app/export_parser.py
app/lang.py
app/llm.py
app/log.py
app/main.py
app/memory.py
app/stt.py
app/style_retrieval.py
app/tts.py
app/vision.py
evals/__init__.py
evals/cases.jsonl
evals/results.json
evals/run_eval.py
requirements.txt
scripts/build_style_index.py
scripts/extract_my_lines.py
tests/conftest.py
tests/test_contacts.py
tests/test_dashboard_auth.py
tests/test_db.py
tests/test_export_parser.py
tests/test_exporter_parser.py
tests/test_lang.py
tests/test_llm_parse.py
tests/test_phone_location.py
tests/test_tts.py
tests/test_webhook_and_controls.py
whatsapp-bridge/bridge_api.js
whatsapp-bridge/index.js
whatsapp-bridge/package-lock.json
whatsapp-bridge/package.json
```

## 2. File Status vs `origin/main` (`git diff --quiet 29a3692 origin/main -- <file>`)

Summary: **42 imported, 30 unmodified, 11 modified, 1 deleted**

### Unmodified (30 files)
Verbatim identical to upstream baseline (`git diff --quiet 29a3692 origin/main -- <file>` exited 0):
```text
app/__init__.py
app/agent_graph.py
app/assistant.py
app/controls.py
app/dashboard.html
app/download_blip.py
app/export_parser.py
app/lang.py
app/llm.py
app/log.py
app/memory.py
app/style_retrieval.py
app/tts.py
evals/__init__.py
evals/cases.jsonl
evals/results.json
evals/run_eval.py
scripts/build_style_index.py
scripts/extract_my_lines.py
tests/test_dashboard_auth.py
tests/test_export_parser.py
tests/test_exporter_parser.py
tests/test_lang.py
tests/test_llm_parse.py
tests/test_phone_location.py
tests/test_tts.py
whatsapp-bridge/bridge_api.js
whatsapp-bridge/index.js
whatsapp-bridge/package-lock.json
whatsapp-bridge/package.json
```
*(Note: `app/assistant.py`, `app/llm.py`, and `app/agent_graph.py` are verified UNMODIFIED in `origin/main`)*.

### Modified (11 files)
Modified between baseline `29a3692` and `origin/main`:
```text
app/contacts.py
app/dashboard.py
app/db.py
app/main.py
app/stt.py
app/vision.py
requirements.txt
tests/conftest.py
tests/test_contacts.py
tests/test_db.py
tests/test_webhook_and_controls.py
```

### Deleted (1 file)
Deleted or renamed in `origin/main`:
```text
app/approvals.py
```

---

## 3. Risk & Difficulty Triage Ranking
Ranking of all 42 files from highest to lowest risk & rewrite difficulty:

| Rank | File | Status | Risk Level | Difficulty | Rationale |
|---|---|---|---|---|---|
| 1 | `whatsapp-bridge/index.js` | Unmodified | High | High | Core WhatsApp Web (`whatsapp-web.js`) connection lifecycle, headless browser automation, unauthenticated IPC risk |
| 2 | `app/main.py` | Modified | High | High | Primary FastAPI server, webhook intake orchestration, channel lifecycles |
| 3 | `app/dashboard.py` | Modified | High | High | Administrative control endpoints, authentication cookies, sensitive setting mutation |
| 4 | `app/dashboard.html` | Unmodified | High | Medium | 997 LOC legacy single-page UI, legacy direct-send JavaScript |
| 5 | `app/db.py` | Modified | High | Medium | Core persistence, audit tables, fail-closed settings schema |
| 6 | `whatsapp-bridge/bridge_api.js` | Unmodified | High | Medium | Local HTTP endpoint bridge communicating with FastAPI backend |
| 7 | `app/agent_graph.py` | Unmodified | High | High | Multi-step LangGraph orchestration, history retrieval, prompt generation |
| 8 | `app/assistant.py` | Unmodified | High | Medium | Assistant OpenAI tool invocation, chat request serialization |
| 9 | `app/llm.py` | Unmodified | Medium | Medium | Structured prompt synthesis, OpenAI client instantiation |
| 10 | `app/contacts.py` | Modified | Medium | Low | Contact mode lookup and phone formatting; scheduled for pure contracts replacement |
| 11 | `app/controls.py` | Unmodified | Medium | Low | Global emergency toggles and configuration setters |
| 12 | `app/stt.py` | Modified | Medium | Low | Speech-to-text wrapper (isolated behind lazy loading) |
| 13 | `app/tts.py` | Unmodified | Medium | Low | Text-to-speech edge synthesis |
| 14 | `app/vision.py` | Modified | Low | Low | Optional image captioning helper |
| 15 | `app/approvals.py` | Deleted | High | Medium | Superseded by pure contracts in `app/contracts/drafts.py` and `app/approvals/` |
| 16 | `app/memory.py` | Unmodified | Low | Low | Conversation message buffer pruning |
| 17 | `app/log.py` | Unmodified | Low | Low | Basic operational console logging |
| 18 | `app/lang.py` | Unmodified | Low | Low | Text language detection heuristics |
| 19 | `app/export_parser.py` | Unmodified | Low | Low | Chat history export file parsing |
| 20 | `app/style_retrieval.py` | Unmodified | Low | Medium | Few-shot style retrieval embeddings |
| 21 | `app/download_blip.py` | Unmodified | Low | Low | Static script to pre-fetch vision models |
| 22 | `scripts/build_style_index.py` | Unmodified | Low | Low | Offline style index embedding generator |
| 23 | `scripts/extract_my_lines.py` | Unmodified | Low | Low | Offline chat export parser for style modeling |
| 24 | `whatsapp-bridge/package.json` | Unmodified | High | Low | Node dependency manifest (`whatsapp-web.js`) |
| 25 | `whatsapp-bridge/package-lock.json` | Unmodified | High | Low | Lockfile tracking pinned Node dependencies |
| 26 | `requirements.txt` | Modified | Medium | Low | Pinned Python dependencies |
| 27 | `evals/run_eval.py` | Unmodified | Low | Low | Test harness evaluating offline agent response quality |
| 28 | `evals/cases.jsonl` | Unmodified | Low | Low | Test cases for eval harness |
| 29 | `evals/results.json` | Unmodified | Low | Low | Historical eval benchmarks |
| 30 | `evals/__init__.py` | Unmodified | Low | Low | Package marker |
| 31 | `app/__init__.py` | Unmodified | Low | Low | Package marker |
| 32 | `tests/conftest.py` | Modified | Medium | Low | Test suite fixtures and mock environments |
| 33 | `tests/test_db.py` | Modified | Medium | Low | Unit tests for persistence and settings |
| 34 | `tests/test_dashboard_auth.py` | Unmodified | Medium | Low | Unit tests for dashboard session authentication |
| 35 | `tests/test_webhook_and_controls.py` | Modified | Medium | Low | Unit tests for webhook intake and toggle controls |
| 36 | `tests/test_contacts.py` | Modified | Low | Low | Unit tests for contact formatting |
| 37 | `tests/test_export_parser.py` | Unmodified | Low | Low | Unit tests for export parsing |
| 38 | `tests/test_exporter_parser.py` | Unmodified | Low | Low | Unit tests for exporter parsing |
| 39 | `tests/test_lang.py` | Unmodified | Low | Low | Unit tests for language detection |
| 40 | `tests/test_llm_parse.py` | Unmodified | Low | Low | Unit tests for LLM schema response parsing |
| 41 | `tests/test_phone_location.py` | Unmodified | Low | Low | Unit tests for phone number parsing |
| 42 | `tests/test_tts.py` | Unmodified | Low | Low | Unit tests for TTS service |

---

## 4. Permission-Request Message to Original Author
Draft formal message for the upstream repository owner (`Shahd132/Whatsapp-Assistant-Agent`):

> **Subject**: Clarification and Permission Request Regarding Whatsapp-Assistant-Agent Code
>
> Dear Shahd,
>
> I hope this note finds you well. I previously built upon and experimented with your repository (`Shahd132/Whatsapp-Assistant-Agent`) to develop `ghostreply`, an open-source personal auto-reply agent with human-in-the-loop safety gating (https://github.com/Natnael-Dev/ghostreply).
>
> Your upstream repository currently does not include an explicit open-source license (`license: null` on GitHub). To ensure strict legal cleanliness and proper intellectual property hygiene, I would like to request your formal clarification:
> 1. Would you be willing to license your original repository under the standard MIT License?
> 2. Alternatively, would you grant permission for the baseline components imported from your prototype to be used and published under the MIT License in `ghostreply` with full author attribution?
>
> I have comprehensively documented the provenance of all 42 files imported from your repository in `docs/PROVENANCE.md` and scoped our project license strictly to original contributions until licensing is resolved.
>
> Thank you very much for your time and foundational work.
>
> Sincerely,  
> Natnael Tezazu
