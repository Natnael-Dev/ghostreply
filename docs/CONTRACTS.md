# ghostreply Core Interface Contracts (v0.1)

**Status:** FROZEN (Phase 1 Baseline)  
**Contract Invariant:** These interfaces define the system-wide seams across channels, safety verifiers, storage, and lifecycle management. Any change or addition to these contracts requires an approved Architecture Decision Record (ADR).

---

## 1. Domain Event & Channel Contracts

### 1.1 InboundEvent Data Model

Every channel adapter translates raw transport payloads into a normalized `InboundEvent`.

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
    text: Optional[str] = None          # Raw incoming text (stripped of link-previews)
    media_type: Optional[MediaType] = None
    media_id: Optional[str] = None      # Internal or channel-specific blob pointer
    
    # Structural safety flags (fail-closed triggers)
    is_group: bool = False              # Must be False for 1-on-1 private reply scope
    is_forwarded: bool = False          # Forwarded text fails closed to HELD
    is_quoted: bool = False             # Quoted context fails closed to HELD
    is_edited: bool = False             # Edited message fails closed to HELD
    has_link_preview: bool = False      # Stripped; treated as untrusted text
    
    # Opaque transport diagnostics
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
```

---

### 1.2 ChannelAdapter Protocol

```python
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
```

---

## 2. Safety Gate & Decision Engine Contracts

### 2.1 GateInput & GateDecision

```python
from enum import Enum
from typing import List

class HoldReasonCode(str, Enum):
    # Channel and Structural Triggers
    GROUP_MESSAGE_IGNORED = "GROUP_MESSAGE_IGNORED"
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
    retrieved_knowledge: List[KnowledgeItem]
    detected_language: str
    language_confidence: float
    has_geez_chars: bool
    quoted_claims_verified: bool
    entailment_verified: bool
    entailment_commits_or_agrees: bool
    is_claim_free_allowlisted: bool
    needs_owner: bool
    kill_switch_active: bool
    shadow_mode_active: bool
    rate_limits_clear: bool

@dataclass(frozen=True)
class GateDecision:
    """Decision output of the safety gate."""
    
    decision: Literal["AUTO_SEND", "HOLD"]
    reason_codes: List[HoldReasonCode]
    evaluated_at: datetime
```

---

## 3. Draft Lifecycle State Machine

### 3.1 DraftState Enum

```python
class DraftState(str, Enum):
    HELD = "HELD"                       # Awaiting human owner action
    APPROVED = "APPROVED"               # Explicitly approved by owner
    SENDING = "sending"                 # Transient lock prior to transport dispatch
    SENT = "SENT"                       # Terminal: Dispatched and confirmed
    REJECTED = "REJECTED"               # Terminal: Explicitly rejected by owner
    EDITED = "EDITED"                   # Owner modified draft; superseded by new draft
    EXPIRED = "EXPIRED"                 # Terminal: TTL reached (24h) without approval
    SEND_UNKNOWN = "SEND_UNKNOWN"       # Terminal: Crash/network partition during dispatch
```

### 3.2 State Transition Matrix

| Initial State | Target State | Actor / Trigger | Guard Conditions / Re-Verifications |
|---|---|---|---|
| `[*]` | `HELD` | Intake / Hold Condition | Any of `MANDATORY_AUTO_SEND_CONDITIONS` fails |
| `[*]` | `SENDING` | Auto-Send Gate | All `MANDATORY_AUTO_SEND_CONDITIONS` pass (pure conjunction) |
| `HELD` | `APPROVED` | Human Owner | If draft age > 30m, requires explicit reconfirmation |
| `HELD` | `REJECTED` | Human Owner | Terminal; invalidates callback nonce |
| `HELD` | `EDITED` | Human Owner | Spawns new draft in `HELD` with fresh nonce and SHA-256 hash |
| `HELD` | `EXPIRED` | System (TTL Worker) | Draft age > 24 hours ($T_{\text{expire}}$) |
| `APPROVED` | `SENDING` | Dispatch Worker | Re-verify kill switch=False, shadow mode=False, rate limits clear |
| `APPROVED` | `HELD` | Dispatch Worker | Re-verification tripped (kill switch engaged or rate cap reached) |
| `SENDING` | `SENT` | Channel Adapter | Socket transmission confirmed by transport |
| `SENDING` | `SEND_UNKNOWN` | Crash Recovery / Timeout | Process killed or network partition; never retried |

**Hold Invariant**: Automated systems, background heuristics, and LLM classifiers CANNOT transition a record from `HELD` to `APPROVED` or `SENT`. Only explicit human interaction by the owner can release a held draft.

---

## 4. Telegram Approval Callback Tokens

Telegram Bot API enforces a **64-byte maximum limit** on `InlineKeyboardButton.callback_data`. Full cryptographic nonces and text bodies are stored server-side.

### 4.1 Callback Data Formats

```
a:<draft_id>       # Approve draft (e.g. a:1042)
r:<draft_id>       # Reject draft (e.g. r:1042)
e:<draft_id>       # Edit draft prompt (e.g. e:1042)
c:<draft_id>       # Confirm stale draft send (> 30 min reconfirmation)
```

### 4.2 Security Protocol
1. **Sender Verification**: The bot callback handler strictly verifies `event.from_user.id == TELEGRAM_OWNER_ID`. Unauthorized users are ignored.
2. **Server-Side Nonce Lookup**: Drafts in `held_queue` store a 128-bit cryptographically secure random nonce (`secrets.token_hex(16)`).
3. **Atomic Consumption**: When an action occurs, the nonce is consumed and state is updated in SQLite atomically. Replayed or stale button presses are rejected with an alert.

---

## 5. Session Vault Security Contract

MTProto userbot credentials are treated as high-privilege keys and never stored in plaintext SQLite databases or unencrypted disk files.

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
        Enforces 5-attempt limit with 15-minute lockout.
        """
        ...
        
    async def lock(self) -> None:
        """Purge decrypted StringSession from memory and return to LOCKED state."""
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

---

## 6. Repository Storage Contracts

All database queries are encapsulated behind typed repository interfaces. Direct SQL queries in application logic are prohibited.

### 6.1 ContactsRepository

```python
@dataclass(frozen=True)
class ContactRecord:
    contact_id: str                     # Namespaced: "wa:<phone>" or "tg:<id>"
    display_name: Optional[str]
    mode: Literal["auto_send", "always_ask", "ignore"]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

class ContactsRepository(Protocol):
    async def get_contact(self, contact_id: str) -> Optional[ContactRecord]: ...
    async def upsert_contact(self, contact: ContactRecord) -> None: ...
    async def list_contacts(self) -> List[ContactRecord]: ...
```

### 6.2 HeldQueueRepository

```python
@dataclass(frozen=True)
class DraftRecord:
    draft_id: int
    channel: ChannelType
    sender_id: str
    chat_id: str
    inbound_message_id: str
    inbound_text: Optional[str]
    draft_text: str
    status: DraftState
    nonce: str                          # 128-bit hex string
    draft_hash: str                     # SHA-256 hex string of draft_text
    reason_codes: List[str]
    created_at: datetime
    updated_at: datetime

class HeldQueueRepository(Protocol):
    async def create_held_draft(self, draft: DraftRecord) -> int:
        """Insert a newly held draft. Returns integer draft_id."""
        ...
        
    async def get_draft(self, draft_id: int) -> Optional[DraftRecord]:
        """Fetch draft by ID."""
        ...
        
    async def transition_state(
        self,
        draft_id: int,
        expected_state: DraftState,
        new_state: DraftState,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Atomically transition draft state from expected_state to new_state.
        Returns True if transition succeeded, False if state had already changed.
        """
        ...
        
    async def list_held_drafts(self, limit: int = 50, offset: int = 0) -> List[DraftRecord]:
        """List active drafts with status HELD."""
        ...
        
    async def expire_stale_drafts(self, ttl_seconds: int = 86400) -> int:
        """Transition HELD drafts older than TTL to EXPIRED. Returns count expired."""
        ...
```

### 6.3 AuditLogRepository (Append-Only)

```python
@dataclass(frozen=True)
class AuditRecord:
    event_id: int
    timestamp: datetime
    event_type: str                     # e.g., "DRAFT_STATE_TRANSITION", "KILL_SWITCH_TOGGLED"
    entity_id: str                      # e.g., "draft:1042", "global:kill_switch"
    actor: str                          # "system", "owner_telegram", "owner_dashboard"
    payload: Dict[str, Any]

class AuditLogRepository(Protocol):
    async def record_event(
        self,
        event_type: str,
        entity_id: str,
        actor: str,
        payload: Dict[str, Any]
    ) -> None:
        """
        Append an immutable event to the audit log.
        Application enforces INSERT-only; UPDATE and DELETE are prohibited.
        """
        ...
        
    async def list_events(self, limit: int = 100, offset: int = 0) -> List[AuditRecord]:
        """Query historical audit events ordered chronologically."""
        ...
```

### 6.4 ControlsRepository

```python
class ControlsRepository(Protocol):
    async def is_kill_switch_active(self) -> bool: ...
    async def set_kill_switch(self, active: bool, actor: str, reason: str) -> None: ...
    async def is_shadow_mode_active(self) -> bool: ...
    async def set_shadow_mode(self, active: bool, actor: str) -> None: ...
```
