"""Data contracts and schemas for safety gate evaluation."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from app.channels.events import InboundEvent


class HoldReasonCode(str, Enum):
    """Named reasons forcing a draft to be held for owner review."""

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
    """Verbatim grounding source item retrieved from context."""

    source_file: str
    verbatim_text: str


@dataclass(frozen=True)
class GateInput:
    """Aggregate context evaluated by the pure conjunction safety gate."""

    event: InboundEvent
    draft_text: str
    contact_mode: Literal["auto_send", "always_ask", "ignore"]
    retrieved_knowledge: list[KnowledgeItem]
    detected_language: str
    language_confidence: float
    has_geez_chars: bool

    # Tri-state verifiers (None = not run or error -> forces HOLD)
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
    """Outcome of safety gate evaluation."""

    decision: Literal["AUTO_SEND", "HOLD"]
    reason_codes: list[HoldReasonCode]
    evaluated_at: datetime
