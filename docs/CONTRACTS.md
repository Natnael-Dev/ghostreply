# ghostreply Core Interface Contracts (v0.2.0)

**Status:** ACTIVE (Revision 0.2.0 - Phase 6.6 Reconciliation, ADR-012)  
**Contract Invariant:** These interfaces define the system-wide seams across channels, safety verifiers, storage, idempotency, and lifecycle management. Any change or addition to these contracts requires an approved Architecture Decision Record (ADR).

---

## 1. Domain Event & Intake Contracts

### 1.1 InboundEvent Data Model

Every channel adapter translates transport payloads into a strictly typed `InboundEvent`.  
**Safety Invariant:** All safety flags are REQUIRED with no default values to prevent accidental fail-open defaults in consumer adapters.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Literal, Optional

ChannelType = Literal["wa", "tg"]
MediaType = Literal["audio", "image", "video", "document"]

@dataclass(frozen=True)
class InboundEvent:
    """Channel-agnostic normalized intake representation of an incoming message."""
    
    channel: ChannelType
    message_id: str                     # Unique ID generated or supplied by the channel
    sender_id: str                      # Namespaced: "wa:<phone_or_lid>" or "tg:<telegram_user_id>"
    chat_id: str                        # Namespaced: "wa:<chat_id>" or "tg:<chat_id>"
    timestamp: datetime                 # Original UTC timestamp from channel
    text: Optional[str]                 # Raw incoming text (stripped of link-previews)
    media_type: Optional[MediaType]
    media_id: Optional[str]             # Internal or channel-specific blob pointer
    
    # Structural safety flags (REQUIRED - no defaults permitted)
    is_group: bool                      # True if message originates from group/supergroup/channel
    is_forwarded: bool                  # True if message was forwarded
    is_quoted: bool                     # True if message quotes or replies to another message
    is_edited: bool                     # True if message is an edited revision
    has_link_preview: bool              # True if message metadata contains link preview cards
    is_bot: bool                        # True if sender is identified as an automated bot
    is_self: bool                       # True if sender is the owner's own user account
    
    # Opaque transport diagnostics
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
```

---

### 1.2 Intake Verdict & Pre-Gate Triage

Messages are evaluated by the Intake Pipeline before reaching the safety gate or LLM draft generation.

```python
from enum import Enum

class IntakeVerdict(str, Enum):
    DROP = "DROP"       # Silently ignored: group chats, bots, self-messages
    PROCESS = "PROCESS" # Eligible 1-on-1 direct message: proceed to pre-filter and gate
```

**Triage Invariant:**
- If `event.is_group == True` OR `event.is_bot == True` OR `event.is_self == True`: verdict is `IntakeVerdict.DROP`.
- Otherwise: verdict is `IntakeVerdict.PROCESS`.

---

### 1.3 ChannelAdapter Protocol & Inbound Delivery

```python
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Optional, Protocol

@dataclass(frozen=True)
class SendResult:
    success: bool
    channel_message_id: Optional[str]
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None

@dataclass(frozen=True)
class ContactProfile:
    contact_id: str                     # Namespaced identifier
    display_name: Optional[str]
    handle_or_phone: Optional[str]

class ChannelAdapter(Protocol):
    """Protocol implemented by WhatsApp and Telegram communication adapters."""
    
    channel_name: ChannelType
    
    async def start(self) -> None:
        """Initialize sockets, background listeners, or bridge connections."""
        ...
        
    async def stop(self) -> None:
        """Gracefully terminate transport connections."""
        ...
        
    async def send_text(self, recipient_id: str, text: str) -> SendResult:
        """Transmit plaintext message to a namespaced recipient."""
        ...
        
    async def get_contact_info(self, contact_id: str) -> ContactProfile:
        """Fetch profile information for a namespaced contact."""
        ...
        
    async def download_media(self, media_id: str) -> bytes:
        """Download raw binary payload for an incoming media item."""
        ...
        
    def register_inbound_handler(
        self,
        handler: Callable[[InboundEvent], Awaitable[None]]
    ) -> None:
        """Register asynchronous callback for normalized inbound message delivery."""
        ...
        
    def stream_inbound(self) -> AsyncIterator[InboundEvent]:
        """Yield inbound events as an asynchronous iterator."""
        ...
```

---

## 2. Safety Gate & Decision Engine Contracts

### 2.1 GateInput & GateDecision

**Verifier Tri-State Invariant:** Verifier fields are `Optional[bool]`.
- `True`: Check ran and verified safe.
- `False`: Check ran and failed verification.
- `None`: Check was not run or experienced an error (fails closed to `HOLD` with `VERIFIER_NOT_RUN` or `VERIFIER_ERROR`).

```python
class HoldReasonCode(str, Enum):
    # Structural Inbound Triggers
    FORWARDED_MESSAGE = "FORWARDED_MESSAGE"
    QUOTED_MESSAGE = "QUOTED_MESSAGE"
    EDITED_MESSAGE = "EDITED_MESSAGE"
    MEDIA_ATTACHMENT_HELD = "MEDIA_ATTACHMENT_HELD"
    LINK_PREVIEW_DETECTED = "LINK_PREVIEW_DETECTED"
    MESSAGE_STALE = "MESSAGE_STALE"
    
    # Language Triggers
    LANGUAGE_NOT_CONFIDENT_ENGLISH = "LANGUAGE_NOT_CONFIDENT_ENGLISH"
    GEEZ_CHARACTERS_DETECTED = "GEEZ_CHARACTERS_DETECTED"
    
    # Keyword / Semantic Pre-Filter Triggers
    INBOUND_FINANCIAL_TRIGGER = "INBOUND_FINANCIAL_TRIGGER"
    INBOUND_RSVP_TRIGGER = "INBOUND_RSVP_TRIGGER"
    INBOUND_PROMISE_TRIGGER = "INBOUND_PROMISE_TRIGGER"
    DRAFT_FINANCIAL_TRIGGER = "DRAFT_FINANCIAL_TRIGGER"
    DRAFT_RSVP_TRIGGER = "DRAFT_RSVP_TRIGGER"
    DRAFT_PROMISE_TRIGGER = "DRAFT_PROMISE_TRIGGER"
    
    # Grounding & Claim Verifier Triggers
    QUOTED_SPAN_UNVERIFIED = "QUOTED_SPAN_UNVERIFIED"
    ENTAILMENT_FAILED = "ENTAILMENT_FAILED"
    ENTAILMENT_COMMITS_OR_AGREES = "ENTAILMENT_COMMITS_OR_AGREES"
    CLAIM_FREE_NOT_ALLOWLISTED = "CLAIM_FREE_NOT_ALLOWLISTED"
    GENERATION_FLAGGED_NEEDS_OWNER = "GENERATION_FLAGGED_NEEDS_OWNER"
    VERIFIER_NOT_RUN = "VERIFIER_NOT_RUN"
    VERIFIER_ERROR = "VERIFIER_ERROR"
    
    # Configuration and Operational Triggers
    CONTACT_MODE_ASK_OR_IGNORE = "CONTACT_MODE_ASK_OR_IGNORE"
    KILL_SWITCH_ENGAGED = "KILL_SWITCH_ENGAGED"
    SHADOW_MODE_ENABLED = "SHADOW_MODE_ENABLED"
    RATE_LIMIT_OR_COOLDOWN_EXCEEDED = "RATE_LIMIT_OR_COOLDOWN_EXCEEDED"

@dataclass(frozen=True)
class KnowledgeItem:
    source_file: str                    # e.g., "about_me.md", "schedule.json"
    verbatim_text: str

@dataclass(frozen=True)
class GateInput:
    """Aggregate context evaluated by the pure conjunction auto-send gate."""
    
    event: InboundEvent
    draft_text: str
    contact_mode: Literal["auto_send", "always_ask", "ignore"]
    retrieved_knowledge: list[KnowledgeItem]
    detected_language: str
    language_confidence: float
    has_geez_chars: bool
    
    # Tri-state verifier fields (None = not run or error -> forces HOLD)
    quoted_claims_verified: Optional[bool]
    entailment_verified: Optional[bool]
    entailment_commits_or_agrees: Optional[bool]
    is_claim_free_allowlisted: Optional[bool]
    
    needs_owner: bool
    kill_switch_active: bool
    shadow_mode_active: bool
    rate_limits_clear: bool

@dataclass(frozen=True)
class GateDecision:
    """Decision output of the safety gate.
    
    SAFETY INVARIANT:
    The gate is hold-only by design. While `AUTO_SEND` exists as a reserved contract state,
    it is NEVER emitted under any circumstance until the shadow evaluation period passes.
    All code paths currently evaluate to `HOLD`.
    """
    
    decision: Literal["AUTO_SEND", "HOLD"]
    reason_codes: list[HoldReasonCode]
    evaluated_at: datetime
```

---

## 3. Draft Lifecycle State Machine & Idempotency

### 3.1 DraftState Enum

```python
class DraftState(str, Enum):
    HELD = "HELD"                       # Awaiting human owner action
    APPROVED = "APPROVED"               # Explicitly approved by owner
    SENDING = "SENDING"                 # Atomic reservation prior to transport dispatch
    SENT = "SENT"                       # Terminal: Dispatched and confirmed
    REJECTED = "REJECTED"               # Terminal: Explicitly rejected by owner
    EDITED = "EDITED"                   # Owner modified draft; superseded by new draft
    EXPIRED = "EXPIRED"                 # Terminal: TTL reached (24h) without approval
    SHADOW_LOGGED = "SHADOW_LOGGED"     # Terminal: Evaluated/approved in shadow mode; logged only
    SEND_UNKNOWN = "SEND_UNKNOWN"       # Terminal: Crash/network partition during dispatch
```

### 3.2 State Transition Matrix

| Initial State | Target State | Actor / Trigger | Guard Conditions / Re-Verifications |
|---|---|---|---|
| `[*]` | `HELD` | Intake / Hold Condition | Any condition in `MANDATORY_AUTO_SEND_CONDITIONS` fails |
| `[*]` | `SENDING` | Auto-Send Gate | All conditions pass AND shadow mode=False |
| `[*]` | `SHADOW_LOGGED` | Auto-Send Gate | All conditions pass AND shadow mode=True (terminal, no dispatch) |
| `HELD` | `APPROVED` | Human Owner | If draft age > 30m, requires explicit reconfirmation |
| `HELD` | `REJECTED` | Human Owner | Terminal; invalidates callback token |
| `HELD` | `EDITED` | Human Owner | Spawns new draft with owner-authored text; old draft becomes EDITED |
| `HELD` | `EXPIRED` | System (TTL Worker) | Draft age > 24 hours ($T_{\text{expire}}$) |
| `APPROVED` | `SENDING` | Dispatch Worker | Re-verify kill switch=False, shadow mode=False, rate limits clear |
| `APPROVED` | `SHADOW_LOGGED` | Dispatch Worker | Shadow mode is active; logs decision without socket transmission |
| `APPROVED` | `HELD` | Dispatch Worker | Re-verification tripped (kill switch engaged or rate cap reached) |
| `SENDING` | `SENT` | Channel Adapter | Socket transmission confirmed by transport |
| `SENDING` | `SEND_UNKNOWN` | Crash Recovery / Timeout | Process killed or network partition; never retried |

**Hold Invariant**: Automated systems and LLM classifiers CANNOT transition a record from `HELD` to `APPROVED` or `SENT`. Only explicit human interaction by the owner can release a held draft.

---

### 3.3 Idempotency & Inbound Ledger

To prevent duplicate auto-replies across bridge restarts and network replays:

```python
class InboundLedger(Protocol):
    """Atomic ledger ensuring exactly-once processing per channel message."""
    
    async def claim(self, channel: ChannelType, message_id: str) -> bool:
        """
        Atomically insert (channel, message_id).
        Returns True if newly claimed. Returns False if already processed or in-flight.
        """
        ...
```

**Database Constraint**:
- The `held_queue` table enforces a `UNIQUE(channel, inbound_message_id)` constraint for all drafts in state `SENDING`, `SENT`, or `SHADOW_LOGGED`.
- Attempted duplicate insertions for the same inbound message fail closed.

---

## 4. Telegram Approval Callback Security

Telegram Bot API enforces a **64-byte maximum limit** on `InlineKeyboardButton.callback_data`.

### 4.1 Scoped Callback Token Format

```
a:<draft_id>:<token>       # Approve draft (e.g. a:1042:x8A9qB_1)
r:<draft_id>:<token>       # Reject draft (e.g. r:1042:x8A9qB_1)
e:<draft_id>:<token>       # Edit draft prompt (e.g. e:1042:x8A9qB_1)
c:<draft_id>:<token>       # Confirm stale draft send (> 30 min reconfirmation)
```

### 4.2 Security Protocol & Token Verification
1. **Token Generation**: Upon draft creation, generate an 8-byte cryptographically secure random token (`secrets.token_urlsafe(8)`).
2. **Server-Side Token Hash**: Store only the SHA-256 digest of the token in SQLite `held_queue.token_hash`.
3. **Card Message Verification**: The approval bot verifies that the callback query originates from `TELEGRAM_OWNER_ID` AND matches the `message_id` of the approval card telegram message.
4. **Constant-Time Comparison**: On callback receipt, compute SHA-256 of the supplied token string and compare against `token_hash` using `hmac.compare_digest`.
5. **Single-Use Consumption**: Once approved, rejected, or expired, the token hash is cleared, invalidating all outstanding buttons.
6. **Immutable Draft Bodies**: `DraftRecord.draft_text` is immutable. Edited drafts generate an entirely new `DraftRecord` with a new token and fresh hash.

---

## 5. Security & Session Vault Contracts

```python
class VaultLockedError(Exception):
    """Raised when an operation requires an unlocked session vault."""
    pass

class VaultLockoutError(Exception):
    """Raised when unlock attempts exceed threshold (5 attempts / 15-minute lockout)."""
    pass

class SessionVault(Protocol):
    """Protocol for Argon2id + AES-256-GCM encrypted credential vault."""
    
    def is_unlocked(self) -> bool:
        """Return True if the vault is unlocked in memory."""
        ...
        
    async def unlock(self, passphrase: str) -> bool:
        """
        Derive AES-256-GCM key via Argon2id and decrypt session string into RAM.
        Enforces 5-attempt limit with persistent 15-minute lockout counter.
        """
        ...
        
    async def lock(self) -> None:
        """
        Purge decrypted StringSession from memory and return to LOCKED state.
        Note: Python memory purge is best-effort due to garbage collection runtime semantics.
        """
        ...
        
    async def get_string_session(self) -> str:
        """
        Retrieve the decrypted Telethon StringSession.
        Raises VaultLockedError if vault is not unlocked.
        """
        ...
        
    async def set_string_session(self, session_str: str, passphrase: str) -> None:
        """Encrypt StringSession with Argon2id and AES-256-GCM; write to disk."""
        ...
```

**Persistence Invariant**: The failed attempt counter and lockout timestamp are persisted in SQLite settings and survive application restarts.

---

## 6. Service & Storage Contracts

### 6.1 Clock & System Abstractions (Injectable & Mockable)

```python
class Clock(Protocol):
    """Time abstraction for deterministic testing of timeouts, TTLs, and stale windows.
    
    RECOMMENDATION (v0.2.0):
    Retain Clock.sleep as an async mockable primitive. In production, it wraps asyncio.sleep.
    In testing and simulation, a mock clock can advance time instantly without wall-clock latency,
    which is essential for deterministic verification of retry delays, backoff, and timeouts.
    """
    
    def now_utc(self) -> datetime: ...
    async def sleep(self, seconds: float) -> None: ...

class LLMClient(Protocol):
    """Mockable LLM completion and judge interface."""
    
    async def generate_reply(
        self,
        inbound_text: str,
        system_prompt: str,
        context_items: list[str]
    ) -> str: ...
    
    async def judge_entailment(
        self,
        draft_text: str,
        context_text: str
    ) -> tuple[bool, bool]:
        """Returns (logically_entailed, commits_or_agrees)."""
        ...

class RateLimiter(Protocol):
    """Stateful persisted rate limiter governing chat caps and global throttling."""
    
    async def check_limits(self, chat_id: str) -> bool:
        """Return True if send rate is within per-chat and global allowances."""
        ...
        
    async def record_send(self, chat_id: str) -> None:
        """Increment counters and reset per-chat cooldown."""
        ...
```

---

### 6.2 HeldQueueRepository & Immutability

```python
@dataclass(frozen=True)
class DraftRecord:
    draft_id: int
    channel: ChannelType
    sender_id: str
    chat_id: str
    inbound_message_id: str
    inbound_text: Optional[str]
    draft_text: str                     # Immutable: no update mutation method exists
    status: DraftState
    token_hash: str                     # SHA-256 hex digest of callback token
    draft_hash: str                     # SHA-256 hex digest of draft_text
    reason_codes: list[str]
    created_at: datetime
    updated_at: datetime

class HeldQueueRepository(Protocol):
    async def create_held_draft(self, draft: DraftRecord) -> int: ...
    async def get_draft(self, draft_id: int) -> Optional[DraftRecord]: ...
    async def transition_state(
        self,
        draft_id: int,
        expected_state: DraftState,
        new_state: DraftState,
        metadata: Optional[dict[str, Any]] = None
    ) -> bool: ...
    async def list_held_drafts(self, limit: int = 50, offset: int = 0) -> list[DraftRecord]: ...
    async def expire_stale_drafts(self, ttl_seconds: int = 86400) -> int: ...
```

---

### 6.3 AuditLogRepository (Append-Only Enforced by Database Triggers)

**Privacy Invariant**: Audit log payloads contain ONLY identifiers, hashes, reason codes, and operational metadata. Message text, names, and phone numbers are strictly prohibited from audit storage.

```python
@dataclass(frozen=True)
class AuditRecord:
    event_id: int
    timestamp: datetime
    event_type: str                     # e.g., "DRAFT_STATE_TRANSITION", "KILL_SWITCH_TOGGLED"
    entity_id: str                      # e.g., "draft:1042", "global:kill_switch"
    actor: str                          # "system", "owner_telegram", "owner_dashboard"
    payload: dict[str, Any]             # Prohibited from containing message text

class AuditLogRepository(Protocol):
    async def record_event(
        self,
        event_type: str,
        entity_id: str,
        actor: str,
        payload: dict[str, Any]
    ) -> None: ...
    
    async def list_events(self, limit: int = 100, offset: int = 0) -> list[AuditRecord]: ...
```

**Database Enforcement**:
The database schema creates SQLite triggers:
```sql
CREATE TRIGGER IF NOT EXISTS prevent_audit_update
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(FAIL, 'Updates to audit_log are prohibited');
END;

CREATE TRIGGER IF NOT EXISTS prevent_audit_delete
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(FAIL, 'Deletions from audit_log are prohibited');
END;
```
