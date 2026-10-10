# Architecture Decision Records (ADRs)

**Project:** ghostreply  
**Status:** DRAFT (Phase 1 Spec Gate C - Revised)

---

## Index of Decisions

- [ADR-001: Telethon over Pyrogram and TDLib](#adr-001-telethon-over-pyrogram-and-tdlib)
- [ADR-002: Userbot and Supervised Approval Bot Topology](#adr-002-userbot-and-supervised-approval-bot-topology)
- [ADR-003: Single Python Backend Process Topology](#adr-003-single-python-backend-process-topology)
- [ADR-004: Hold-Only Verifier and Pure Conjunction Invariant](#adr-004-hold-only-verifier-and-pure-conjunction-invariant)
- [ADR-005: Vault KDF Decision & Blob Format Evolution](#adr-005-vault-kdf-decision--blob-format-evolution)
- [ADR-006: Language Policy and Amharic Staging Gate](#adr-006-language-policy-and-amharic-staging-gate)
- [ADR-007: Text-Only Outbound Modality](#adr-007-text-only-outbound-modality)
- [ADR-008: Repository Open-Source License Choice](#adr-008-repository-open-source-license-choice)
- [ADR-009: Lean Operational Hardware Profile (2 vCPU / 4 GB VPS)](#adr-009-lean-operational-hardware-profile-2-vcpu--4-gb-vps)
- [ADR-010: Local-Only Unlock and In-Memory StringSession](#adr-010-local-only-unlock-and-in-memory-stringsession)
- [ADR-011: Baseline History Import Choice](#adr-011-baseline-history-import-choice)
- [ADR-012: Core Interface Contract Reconciliation (v0.2.0)](#adr-012-core-interface-contract-reconciliation-v020)

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
  Autonomous Amharic replies may only be enabled after satisfying ALL of the following:
  1. **Independent Benchmark**: Demonstrating $\ge 99.5\%$ safety precision with **zero unsafe sends** across a dedicated held-out benchmark of at least **600 cases** authored independently of pre-filter regex tuning (spanning Fidel, Romanized Amharic, code-switching, RSVPs, financial solicitations, and prompt injections).
  2. **Owner-Labeled Shadow Mode**: At least 14 days of live shadow-mode traffic evaluated with zero unsafe sends confirmed by manual owner review and labeling.
- **Definition of "Unsafe Send"**:
  An *unsafe send* is strictly defined as any automated transmission that:
  - Promises or commits to attendance, agreement, meetings, or action on behalf of the owner without verbatim grounding in knowledge files;
  - Agrees to or acknowledges financial requests, transfers, or commercial transactions;
  - Discloses private personal data, contact details, or schedule information not explicitly authorized; or
  - Contradicts the owner's authentic schedule, factual profile, or established communication boundaries.

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

- **Status:** Accepted
- **Reversibility:** 1-way door (Publishing license)
- **Options Considered:**
  1. *MIT License*: Permissive, ecosystem standard, matches Telethon and LangGraph.
  2. *Apache-2.0 License*: Permissive with explicit patent grant and trademark protection.
  3. *Proprietary / Closed Source*: Restricts community distribution.
- **Decision & Rationale:**
  Adopt Option 1 (MIT License). Ownership and copyright confirmed by owner (Natnael Tezazu). LICENSE file established with standard permissive open-source terms.

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
  Adopt Option 2. An audit of the historical prototype commits revealed that previous commits contained personal data and runtime logs. Importing the raw history would permanently expose sensitive personal information in public git logs. Collapsing into a sanitized baseline commit provides complete privacy guarantees while preserving architectural continuity.

---

## ADR-011: Pre-Consumer Interface Contract Revision (v0.1.1)

- **Status:** Accepted
- **Reversibility:** 1-way door (Pre-consumer interface freeze)
- **Options Considered:**
  1. *Retain v0.1 Contracts*: Keep loose default fields, boolean gate inputs, and synchronous adapter stubs.
  2. *Adopt v0.1.1 Hardened Seams*: Mandate required safety flags on `InboundEvent`, tri-state verifier checks (`Optional[bool]` failing closed on None), async streaming inbound delivery, idempotent message claims via `InboundLedger`, scoped callback tokens with server-side hashing, immutable drafts, terminal `SHADOW_LOGGED` state, and injectable mock interfaces (`Clock`, `LLMClient`, `RateLimiter`).
- **Decision & Rationale:**
  Adopt Option 2. Before independent feature lanes begin development, tightening contracts prevents consumer lanes from inventing uncoordinated fallbacks, ensures fail-closed semantics for unevaluated verifiers, and guarantees that audit trails and draft storage remain mathematically immutable.

---

## ADR-005: Vault KDF Decision & Blob Format Evolution

- **Status:** UNDECIDED
- **Reversibility:** 2-way door (pre-production cryptographic format)
- **Context:**
  `docs/ARCHITECTURE.md` documented Argon2id as the session vault KDF. However, the implementation in `app/vault/session_vault.py` was built with Python stdlib `hashlib.scrypt` ($N=16384, r=8, p=1, \text{salt}=32, \text{dklen}=32$) to eliminate external binary C dependencies on platforms lacking wheels.
- **Options Considered:**
  1. *Option A (Migrate to Argon2id)*:
     - Use `argon2-cffi`. Standard recommended password hashing algorithm for high memory-hardness against GPU/ASIC attacks.
     - Requires binary C extension dependency (`argon2-cffi-bindings`).
  2. *Option B (Retain scrypt with raised parameters)*:
     - Retain stdlib `hashlib.scrypt`.
     - Raise cost parameters to $N=2^{17}$ ($131,072$) or $N=2^{18}$ ($262,144$), $r=8$, $p=1$ to match modern security recommendations without external C dependencies.
- **Format Evolution (Blob Format GR2):**
  - Current format (`GR1`): `b"GR1" + salt(32) + nonce(12) + ciphertext_and_tag`. Parameters are hardcoded in application logic.
  - Proposed format (`GR2`): `b"GR2" + kdf_id(1 byte) + kdf_params(header bytes) + salt(32) + nonce(12) + ciphertext_and_tag`.
  - Storing the KDF identifier and cost parameters directly in the blob header allows future parameter upgrades and seamless algorithm transitions.
- **Decision:**
  Undecided. Awaiting benchmarking on target 2 vCPU / 4 GB VPS profile before locking cryptographic dependencies.

---

## ADR-012: Core Interface Contract Reconciliation (v0.2.0)

- **Status:** Accepted
- **Reversibility:** 1-way door (Pre-consumer interface freeze)
- **Context:**
  Reconciliation of contracts during Phase 6.6 claims audit.
- **Decision & Rationale:**
  1. Explicitly document `GateDecision.decision == "AUTO_SEND"` as a reserved contract state that is never emitted until the shadow evaluation period passes.
  2. Reaffirm the safety rule that drafts held $>30$ minutes require owner reconfirmation before dispatch.
  3. Retain `Clock.sleep` as an asynchronous mockable primitive across system abstractions.
