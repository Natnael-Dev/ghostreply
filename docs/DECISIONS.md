# Architecture Decision Records (ADRs)

**Project:** ghostreply  
**Status:** DRAFT (Phase 1 Spec Gate C - Revised)

---

## Index of Decisions

- [ADR-001: Telethon over Pyrogram and TDLib](#adr-001-telethon-over-pyrogram-and-tdlib)
- [ADR-002: Userbot and Supervised Approval Bot Topology](#adr-002-userbot-and-supervised-approval-bot-topology)
- [ADR-003: Single Python Backend Process Topology](#adr-003-single-python-backend-process-topology)
- [ADR-004: Hold-Only Verifier and Pure Conjunction Invariant](#adr-004-hold-only-verifier-and-pure-conjunction-invariant)
- [ADR-005: Language Policy and Amharic Staging Gate](#adr-005-language-policy-and-amharic-staging-gate)
- [ADR-006: Text-Only Outbound Modality](#adr-006-text-only-outbound-modality)
- [ADR-007: Repository Open-Source License Choice](#adr-007-repository-open-source-license-choice)
- [ADR-008: Lean Operational Hardware Profile (2 vCPU / 4 GB VPS)](#adr-008-lean-operational-hardware-profile-2-vcpu--4-gb-vps)
- [ADR-009: Local-Only Unlock and In-Memory StringSession](#adr-009-local-only-unlock-and-in-memory-stringsession)
- [ADR-010: Baseline History Import Choice](#adr-010-baseline-history-import-choice)

---

## ADR-001: Telethon over Pyrogram and TDLib

- **Status:** Accepted
- **Reversibility:** 2-way door (adapter-isolated)
- **Options Considered:**
  1. *Telethon* (Pure Python MTProto client, active maintenance, MIT).
  2. *Pyrogram* (Main project unmaintained since 2023, LGPLv3 [VERIFIED via PyPI metadata]).
  3. *Pyrofork* (Community fork reported archived in 2026 [CLAIMED]).
  4. *TDLib via python-telegram / ctypes* (C++ compilation overhead, heavier operational dependencies).
- **Decision & Rationale:**
  Adopt `telethon` (pinned to `1.45.0` [VERIFIED via `pip index versions telethon` on 2026-10-07]). Telethon is pure Python, natively asynchronous, licensed under permissive MIT, and eliminates binary compilation requirements.
- **Trade-offs:**
  Telethon v1 API is mature and battle-tested for 1-on-1 private messaging. Potential future v2 migration path is currently unassessed [CLAIMED/UNKNOWN].

---

## ADR-002: Userbot and Supervised Approval Bot Topology

- **Status:** Accepted
- **Reversibility:** 2-way door
- **Options Considered:**
  1. *Userbot only*: Owner interacts with saved messages or a self-chat for approvals.
  2. *Official Bot only*: Cannot read or send direct messages on personal Telegram account.
  3. *Hybrid Topology*: Telethon MTProto userbot monitors personal account; dedicated Official Bot (`TELEGRAM_APPROVAL_BOT_USERNAME`) manages owner approvals via inline buttons.
- **Decision & Rationale:**
  Adopt Option 3 (Hybrid). The official Bot API instance provides an intuitive inline keyboard UI (`[Approve]`, `[Edit]`, `[Reject]`) with interactive callback queries, while the MTProto userbot handles personal message intake and dispatch.
- **Trade-offs:**
  Requires managing two sets of Telegram credentials (`api_id`/`api_hash` for userbot and `bot_token` for approval bot). Mitigated by unified supervision.

---

## ADR-003: Single Python Backend Process Topology

- **Status:** Accepted
- **Reversibility:** 2-way door
- **Options Considered:**
  1. *Multi-daemon microservices*: Separate processes for FastAPI, Celery workers, userbot daemon, and approval bot daemon.
  2. *Single Python process + Node bridge*: One Python process managing FastAPI and background `asyncio` tasks, alongside the separate Node.js WhatsApp bridge process.
- **Decision & Rationale:**
  Adopt Option 2. Consolidating the Python side into a single application process minimizes RAM overhead, avoids inter-process message broker dependencies (Redis/RabbitMQ), and allows in-memory state coordination. The Node.js WhatsApp bridge remains a standalone lightweight process communicating over loopback HTTP.
- **Trade-offs:**
  A fatal uncaught exception in the Python event loop could impact all background tasks. Mitigated by `asyncio.TaskGroup` supervision with restart policies.

---

## ADR-004: Hold-Only Verifier and Pure Conjunction Invariant

- **Status:** Accepted
- **Reversibility:** 1-way door (Fundamental Safety Invariant)
- **Options Considered:**
  1. *Weighted scoring / confidence thresholds*: Composite score triggering auto-send above threshold.
  2. *Pure Conjunction with Hold-Only Rule*: Explicit named conditions (`MANDATORY_AUTO_SEND_CONDITIONS`). Every check is an independent Boolean assertion. Failure of any single condition unconditionally forces `HELD`.
- **Decision & Rationale:**
  Adopt Option 2. In our fail-closed architecture, automated checks may only transition a draft to `HELD`. Only explicit owner actions may transition out of `HELD`.
- **Trade-offs:**
  Accepts a higher false-hold rate to achieve absolute zero false-sends.

---

## ADR-005: Language Policy and Amharic Staging Gate

- **Status:** Accepted
- **Reversibility:** 2-way door
- **Options Considered:**
  1. *Multi-lingual auto-send immediately*: Attempt automated replies in Amharic (Fidel & Romanized) from day one.
  2. *English auto-send MVP; Amharic Hold-by-Default*: Non-English inbound messages produce drafts but are unconditionally held for human approval until formal evaluation gates pass.
- **Decision & Rationale:**
  Adopt Option 2. The primary rationale is that safety gate and verifier accuracy on Amharic is currently unmeasured in production. To protect against hallucinated promises or tone failures, all non-English messages fail closed into `HELD`.
- **Phase 7 Exit Criteria**:
  Autonomous Amharic replies may only be enabled after demonstrating $\ge 99.5\%$ safety precision with zero unsafe false-sends across a dedicated evaluation benchmark of $\ge 200$ test cases.

---

## ADR-006: Text-Only Outbound Modality

- **Status:** Accepted
- **Reversibility:** 2-way door
- **Options Considered:**
  1. *Voice reply synthesis via edge-tts*: Synthesize outbound voice notes using unofficial browser endpoints.
  2. *Strict Text-Only Outbound*: Disable outgoing voice note synthesis.
- **Decision & Rationale:**
  Adopt Option 2. Edge-tts relies on unofficial endpoints prone to rate limits and breaking changes. In addition, synthetic voice messages carry elevated impersonation risks. Outbound communication remains text-only. Inbound voice notes are held by default.

---

## ADR-007: Repository Open-Source License Choice

- **Status:** Proposed, pending ownership confirmation
- **Reversibility:** 1-way door (Publishing license)
- **Options Considered:**
  1. *MIT License*: Permissive, ecosystem standard, matches Telethon and LangGraph.
  2. *Apache-2.0 License*: Permissive with explicit patent grant and trademark protection.
  3. *Proprietary / Closed Source*: Restricts community distribution.
- **Decision & Rationale:**
  Propose MIT (or Apache-2.0 as alternative permissive option). Final license text and copyright attribution wait for owner confirmation of upstream repository relationships.

---

## ADR-008: Lean Operational Hardware Profile (2 vCPU / 4 GB VPS)

- **Status:** Accepted
- **Reversibility:** 2-way door
- **Options Considered:**
  1. *Heavy ML Profile*: Load local Whisper, BLIP, and embeddings in host memory ($\ge 8\text{ GB RAM}$).
  2. *Lean Operational Profile*: Offload LLM inference to remote API; keep local STT/BLIP disabled by default; run comfortably on 2 vCPU / 4 GB RAM VPS.
- **Decision & Rationale:**
  Adopt Option 2. Minimizes resource footprint, eliminates OOM risks, and avoids GPU hosting requirements.

---

## ADR-009: Local-Only Unlock and In-Memory StringSession

- **Status:** Accepted
- **Reversibility:** 1-way door (Security Architecture)
- **Options Considered:**
  1. *Plaintext session file on disk*: Standard Telethon `.session` SQLite database.
  2. *Chat-based remote unlock*: Unlock MTProto session via Telegram command.
  3. *Local-only unlock with StringSession*: Session exists in RAM as a Telethon `StringSession`; encrypted at rest via Argon2id + AES-256-GCM; unlocked exclusively via loopback (`127.0.0.1`) dashboard or CLI.
- **Decision & Rationale:**
  Adopt Option 3. Plaintext files on disk risk exposure during backups or file audits. Chat-based unlock violates the principle of "restrict remotely, loosen locally". Local unlock restricts secret handling to local administrative channels.

---

## ADR-010: Baseline History Import Choice

- **Status:** Accepted
- **Reversibility:** 1-way door (Repository History Publishing)
- **Options Considered:**
  1. *Import Full Git History*: Retain full historical commits from the original prototype.
  2. *Single Clean Baseline Commit*: Import a clean, sanitized snapshot of the codebase as a single baseline commit (`import baseline from the original whatsapp repo (sanitized)`).
- **Decision & Rationale:**
  Adopt Option 2. An audit of the historical prototype commits revealed that previous commits contained personal data and runtime logs. Importing the raw history would permanently expose sensitive personal information in public git logs. Collapsing into a sanitized baseline commit provides complete privacy guarantees while preserving architectural continuity. Attribution details will be finalized upon owner confirmation.
