# Architecture Decision Records (ADRs)

**Project:** ghostreply  
**Status:** DRAFT (Phase 1 Spec Gate C)

---

## Index of Decisions

- [ADR-001: Telethon over Pyrogram and TDLib](#adr-001-telethon-over-pyrogram-and-tdlib)
- [ADR-002: Userbot and Supervised Approval Bot Topology](#adr-002-userbot-and-supervised-approval-bot-topology)
- [ADR-003: Single Process Application Topology](#adr-003-single-process-application-topology)
- [ADR-004: Hold-Only Verifier and Pure Conjunction Invariant](#adr-004-hold-only-verifier-and-pure-conjunction-invariant)
- [ADR-005: Language Policy and Amharic Staging](#adr-005-language-policy-and-amharic-staging)
- [ADR-006: Text-Only Outbound Modality](#adr-006-text-only-outbound-modality)
- [ADR-007: Repository Open-Source License (MIT)](#adr-007-repository-open-source-license-mit)
- [ADR-008: Lean Operational Hardware Profile (2 vCPU / 4 GB VPS)](#adr-008-lean-operational-hardware-profile-2-vcpu--4-gb-vps)
- [ADR-009: Local-Only Unlock and At-Rest Session Encryption](#adr-009-local-only-unlock-and-at-rest-session-encryption)
- [ADR-010: Baseline History Import Choice](#adr-010-baseline-history-import-choice)

---

## ADR-001: Telethon over Pyrogram and TDLib

- **Status:** Accepted
- **Reversibility:** 2-way door (adapter-isolated)
- **Options Considered:**
  1. *Telethon* (Pure Python MTProto client, active maintenance, MIT).
  2. *Pyrogram* (Inactive since 2023, fork fragmentation, GPLv3).
  3. *Pyrofork* (Archived 2026, uncertain long-term maintenance).
  4. *TDLib via python-telegram / ctypes* (Heavy C++ binaries, compilation overhead, operational complexity).
- **Decision & Rationale:**
  Adopt `telethon` (pinned to `1.45.0`, verified from PyPI). Telethon is pure Python, natively supports async/await, runs directly within our single-process asyncio loop without C++ toolchains, and is licensed under permissive MIT.
- **Trade-offs:**
  Telethon v1 API is mature but lacks some v2 features. However, for 1-on-1 private messaging and bot polling, v1.45.0 provides maximum stability.

---

## ADR-002: Userbot and Supervised Approval Bot Topology

- **Status:** Accepted
- **Reversibility:** 2-way door
- **Options Considered:**
  1. *Userbot only*: Owner interacts with saved messages or a self-chat for approvals.
  2. *Official Bot only*: Cannot read or send direct messages on personal Telegram account.
  3. *Hybrid Topology*: Telethon MTProto userbot monitors personal account; dedicated Official Bot (@ApprovalBot) manages owner approvals via inline buttons.
- **Decision & Rationale:**
  Adopt Option 3 (Hybrid). An official Bot API instance provides native inline keyboard UI (`[Approve]`, `[Edit]`, `[Reject]`) with interactive callback queries, while the MTProto userbot handles personal message intake and dispatch.
- **Trade-offs:**
  Requires managing two Telegram credentials (`api_id`/`api_hash` for userbot and `bot_token` for approval bot). Mitigated by unified supervision.

---

## ADR-003: Single Process Application Topology

- **Status:** Accepted
- **Reversibility:** 2-way door
- **Options Considered:**
  1. *Microservices*: Separate processes for FastAPI, Celery workers, userbot daemon, and approval bot daemon.
  2. *Single Process with asyncio TaskGroup*: One FastAPI application process orchestrating background tasks under a shared event loop.
- **Decision & Rationale:**
  Adopt Option 2 (Single Process). Running a unified process drastically reduces RAM consumption on a 2 vCPU / 4 GB VPS, eliminates inter-process message broker dependencies (Redis/RabbitMQ), and simplifies deployment to a single systemd service unit.
- **Trade-offs:**
  A fatal uncaught exception in the process terminates all tasks. Mitigated by wrapping long-running tasks in structured exception handlers with restart policies.

---

## ADR-004: Hold-Only Verifier and Pure Conjunction Invariant

- **Status:** Accepted
- **Reversibility:** 1-way door (Fundamental Safety Invariant)
- **Options Considered:**
  1. *Heuristic weighted scoring*: Composite confidence score triggering auto-send above threshold.
  2. *Pure Conjunction with Hold-Only Rule*: Every check is an independent Boolean assertion. All 11 checks must evaluate to `true` to send. Any check failure unconditionally locks the status to `HELD`.
- **Decision & Rationale:**
  Adopt Option 2. Under zero circumstances may an AI heuristic or secondary evaluation override an earlier `HOLD`. Failsafe behavior requires fail-closed architecture to prevent hallucinated commitments or unauthorized messages.
- **Trade-offs:**
  Higher rate of false holds (lower automation rate). This trade-off is accepted by design: privacy and correctness strictly supersede reply velocity.

---

## ADR-005: Language Policy and Amharic Staging

- **Status:** Accepted
- **Reversibility:** 2-way door
- **Options Considered:**
  1. *Full multi-lingual auto-send*: Attempt automated replies in Amharic (Fidel & Romanized) immediately.
  2. *English auto-send MVP; Amharic Hold-by-Default*: Non-English inbound messages produce drafts but are unconditionally held for human approval until formal evaluation gates pass.
- **Decision & Rationale:**
  Adopt Option 2. Local speech and translation models exhibit elevated error rates on Amharic. Holding all non-English messages prevents miscommunications while allowing the owner to build confidence in draft quality. Automated Amharic sends are deferred to Phase 7.
- **Trade-offs:**
  All Amharic interactions require manual approval tap in the MVP.

---

## ADR-006: Text-Only Outbound Modality

- **Status:** Accepted
- **Reversibility:** 2-way door
- **Options Considered:**
  1. *Voice reply generation via edge-tts*: Synthesize outbound voice notes using unofficial Edge browser endpoints.
  2. *Strict Text-Only Outbound*: Disable audio generation entirely in MVP.
- **Decision & Rationale:**
  Adopt Option 2. Edge-tts relies on unofficial endpoints prone to rate-limiting and breaking changes. Furthermore, synthetic voice notes increase human impersonation risk. Outbound communication remains text-only.
- **Trade-offs:**
  Cannot auto-respond to voice notes with voice notes. Inbound voice notes are held for owner review.

---

## ADR-007: Repository Open-Source License (MIT)

- **Status:** Proposed, pending ownership confirmation
- **Reversibility:** 1-way door (Publishing license)
- **Options Considered:**
  1. *MIT License*: Permissive, ecosystem-standard, matches Telethon and LangGraph dependencies.
  2. *AGPLv3 License*: Copyleft, restrictive, incompatible with downstream embedding.
  3. *Proprietary / Closed Source*: Prevents open collaboration.
- **Decision & Rationale:**
  Propose MIT License. Dependent on owner verification regarding upstream repository (`Whatsapp-Assistant-Agent`) authorship. Zero code is copied from AGPL projects; ideas from upstream research are credited with proper attribution.
- **Trade-offs:**
  Permissive licensing allows commercial reuse by third parties.

---

## ADR-008: Lean Operational Hardware Profile (2 vCPU / 4 GB VPS)

- **Status:** Accepted
- **Reversibility:** 2-way door
- **Options Considered:**
  1. *Heavy In-Process ML Profile*: Run local Whisper (~2.1 GB) + BLIP (~1.6 GB) + E5 (~800 MB), requiring $\ge$ 8 GB RAM VPS (~$7.40/mo).
  2. *Lean Operational Profile*: Offload LLM inference to remote API; disable local STT/BLIP by default; fit within 2 vCPU / 4 GB RAM VPS (~$4.15/mo).
- **Decision & Rationale:**
  Adopt Option 2. Keeps hosting costs low, guarantees memory safety without Linux OOM crashes, and eliminates GPU requirements.

---

## ADR-009: Local-Only Unlock and At-Rest Session Encryption

- **Status:** Accepted
- **Reversibility:** 1-way door (Security Architecture)
- **Options Considered:**
  1. *Plaintext session storage*: Store `.session` file directly on disk.
  2. *Chat-based unlock*: Allow owner to send `/unlock <passphrase>` via Telegram bot.
  3. *Local-only unlock with Argon2id + AES-256-GCM*: Encrypt session file at rest; accept unlock secret exclusively via HTTPS web dashboard, local SSH, or systemd credentials.
- **Decision & Rationale:**
  Adopt Option 3. Chat channels are untrusted transport vectors. If an attacker hijacked the Telegram session or spoofed the chat ID, chat-based unlock would compromise the master secret. The unlock secret is strictly isolated from the dashboard login password.
- **Trade-offs:**
  Requires the owner to access the local HTTPS dashboard or SSH terminal after each server reboot to enter the unlock secret.

---

## ADR-010: Baseline History Import Choice

- **Status:** Accepted
- **Reversibility:** 1-way door (Repository History Publishing)
- **Options Considered:**
  1. *Import Full Git History*: Retain all 6 historical commits from the original WhatsApp prototype.
  2. *Single Clean Baseline Commit*: Import a sanitized snapshot of the codebase as a single initial commit (`import baseline from the original whatsapp repo (sanitized)`) with attribution to the upstream repository.
- **Decision & Rationale:**
  Adopt Option 2. An exhaustive scan of the 6 historical commits revealed 110 sensitive instances including 86 real phone numbers in committed log files (`data/app.log`), personal names in commit messages, and real chat logs in `data/style_examples.md`. Publishing raw history would permanently leak personal data to the public.
- **Trade-offs:**
  Historical commit granularity is collapsed into a single clean baseline. Upstream provenance is preserved via explicit attribution in documentation and commit messages.

---

## Attribution and Dependency License Notes

- **Upstream Origin**: Core concepts and initial WhatsApp LangGraph agent derived from `https://github.com/Shahd132/Whatsapp-Assistant-Agent`.
- **Telethon**: Licensed under MIT (LonamiWebs). Pinned dependency `telethon==1.45.0`.
- **LGPL Compliance**: Any LGPL dependencies (e.g. optional media utilities) must be consumed strictly as dynamic external package dependencies without vendoring.
- **AGPL Exclusion**: Zero code has been copied from AGPL projects.
