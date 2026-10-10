# GhostReply System State

**Current Branch:** `ghostreply/phase-6.6`  
**Base Commit:** `7fbfb78492686282724e6838c087679cbdb3dc6a` (matches `origin/main`)  
**Verified Test Suite:** 150 passed (offline, Python 3.13.15, pytest 9.1.1)

---

## 1. Provenance and Commit History

GhostReply was initialized on `2026-03-31` from an unsanitized prototype import (`29a3692`), followed by an immediate sanitization pass (`3ebdfba`). Architecture refactoring and safety engineering progressed across 14 merged pull requests:

| PR | Merge SHA | Description |
|---|---|---|
| #1 | `8e73454` | add test scaffold and test env configuration |
| #2 | `25bc2f1` | dashboard basic authentication and secure defaults |
| #3 | `564472f` | isolate tts and exporter services behind interfaces |
| #4 | `96f059d` | inbound idempotency ledger with claim state machine |
| #5 | `d555c88` | secure secrets loading and environment validation |
| #6 | `c43a0e6` | intake routing and filtering before gate |
| #7 | `38b4df3` | phone number and location parsing utilities |
| #8 | `266fdb7` | decouple llm response parsing with schema validation |
| #9 | `3ac2e0a` | channel seam and outbound transport interfaces |
| #10 | `b47cc62` | safety gate orchestrator and language prefilters |
| #11 | `98d2e1f` | encrypted session vault with persistent lockout |
| #12 | `9869b9c` | approval core state machine, signed tokens, owner guard |
| #13 | `e917fad` | dispatch rechecks, clock injection, rate limiting, and e2e integration |
| #14 | `7fbfb78` | audit log sqlite immutability triggers and adversarial test suite |

---

## 2. Verified Architectural Invariants

- **Idempotency Ledger:** `SqliteInboundLedger.claim()` enforces atomic single-winner claiming (`tests/test_inbound_ledger.py`).
- **Owner Guard:** Approval callbacks reject requests whose user ID differs from `APPROVAL_OWNER_ID` (`app/approvals/owner_guard.py`).
- **Constant-Time Comparison:** Callback HMAC signatures and tokens evaluated using `hmac.compare_digest` (`app/approvals/tokens.py`).
- **Hold-Only Gate:** `SafetyGateOrchestrator` returns `GateOutcome.HOLD` across all evaluated paths; no automated send outcome is ever generated without human approval (`tests/test_safety_gate_orchestrator.py`).
- **Dispatch Rechecks:** `dispatch_with_rechecks()` re-evaluates the global kill switch and shadow-mode status at invocation time before delegating to the transport (`app/channels/dispatcher.py#L42-L55`).
- **Fail-Closed Defaults:** Database control defaults configured to `auto_reply="0"`, `direct_send="0"`, and `contact_mode="hold"` (`app/db.py#L32-L42`).

---

## 3. Known Discrepancies and Open Architectural Items

The deep reconnaissance and claims audit conducted on commit `7fbfb78` identified the following discrepancies against original documentation:

1. **GateDecision Bi-state vs Tri-state (Claim C4):**
   - Code emits `GateOutcome.HOLD` and `GateOutcome.DROP`. `GateOutcome.AUTO_SEND` exists in contracts but is intentionally never emitted. Missing verifier produces `GateOutcome.HOLD` with reason `VERIFIER_NOT_RUN`, rather than a distinct third decision state.
2. **Vault KDF Specification vs Implementation (Claim C10, ADR-005):**
   - `docs/ARCHITECTURE.md` states Argon2id is used. The implementation in `app/vault/session_vault.py#L11` uses Python stdlib `hashlib.scrypt` ($N=2^{14}, r=8, p=1$). Tracked in `ADR-005` (undecided).
3. **Audit Immutability SQLite Triggers (Claim C11):**
   - Triggers intercept `UPDATE` and `DELETE` on `audit_log`. However, `INSERT OR REPLACE INTO audit_log` bypasses the `BEFORE UPDATE` trigger by firing an internal delete. Triggers must be expanded to cover `BEFORE INSERT` checks or table constraints.
4. **Draft Age Reconfirmation (Contract Discrepancy):**
   - `docs/CONTRACTS.md#L309` specifies drafts held $>30$ minutes must require reconfirmation before sending. Currently not enforced in `app/approvals/state.py`. Tracked for Phase 7 implementation with strict xfail test.
5. **Multiple Un-gated Send Call Sites (Claim C16):**
   - Direct HTTP POST routes (`POST /send_message` in `app/main.py` and assistant execution in `app/dashboard.py`) send directly to the WhatsApp bridge without passing through `dispatch_with_rechecks()` or `SafetyGateOrchestrator`. Tracked for Phase 7.1 consolidation.
6. **Cross-Lane Import Coupling (Claim C17):**
   - Circular import dependency exists: `app.gate.models` -> `app.channels.events` -> `app.channels.dispatcher` -> `app.approvals.state` -> `app.approvals.repository` -> `app.gate.prefilter` -> `app.gate.models`. Requires extracting shared contracts to `app/contracts/` in Phase 7.0.
