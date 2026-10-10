"""Pre-filters for structural triggers, stale messages, and keywords."""
import re
from datetime import datetime, timezone
from typing import Optional, Protocol

from app.channels.events import InboundEvent
from app.gate.models import HoldReasonCode

STALE_THRESHOLD_SECONDS = 300.0  # 5 minutes

FINANCIAL_PATTERN = re.compile(
    r"(?i)(\$|€|£|usd|etb|wire|bank|transfer|payment|invoice|credit card|"
    r"crypto|bitcoin|eth|send money|pay me)"
)
RSVP_PATTERN = re.compile(
    r"(?i)(\brsvp\b|attending|will you come|are you coming|wedding|party|"
    r"invitation|see you there)"
)
PROMISE_PATTERN = re.compile(
    r"(?i)(\bi promise\b|\bi guarantee\b|\bi will definitely\b|"
    r"\bcount on me\b|\bi swear\b)"
)


class Clock(Protocol):
    """Injectable time provider for deterministic testing."""

    def now_utc(self) -> datetime:
        ...


class SystemClock:
    """Standard system clock returning UTC datetime."""

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)


def evaluate_prefilters(
    event: InboundEvent,
    draft_text: str = "",
    clock: Optional[Clock] = None,
) -> list[HoldReasonCode]:
    """Evaluate structural, temporal, and keyword pre-filters."""
    reasons: list[HoldReasonCode] = []
    _check_structural(event, reasons)
    _check_staleness(event, reasons, clock or SystemClock())
    _check_keywords(event.text or "", draft_text, reasons)
    return reasons


def _check_structural(
    event: InboundEvent, reasons: list[HoldReasonCode]
) -> None:
    if event.is_forwarded:
        reasons.append(HoldReasonCode.FORWARDED_MESSAGE)
    if event.is_quoted:
        reasons.append(HoldReasonCode.QUOTED_MESSAGE)
    if event.is_edited:
        reasons.append(HoldReasonCode.EDITED_MESSAGE)
    if event.has_link_preview:
        reasons.append(HoldReasonCode.LINK_PREVIEW_DETECTED)
    if event.media_type is not None or event.media_id is not None:
        reasons.append(HoldReasonCode.MEDIA_ATTACHMENT_HELD)


def _check_staleness(
    event: InboundEvent,
    reasons: list[HoldReasonCode],
    clock: Clock,
) -> None:
    now = clock.now_utc()
    msg_time = event.timestamp
    if msg_time.tzinfo is None:
        msg_time = msg_time.replace(tzinfo=timezone.utc)
    delta = (now - msg_time).total_seconds()
    if delta > STALE_THRESHOLD_SECONDS:
        reasons.append(HoldReasonCode.MESSAGE_STALE)


def _check_keywords(
    inbound_text: str,
    draft_text: str,
    reasons: list[HoldReasonCode],
) -> None:
    if FINANCIAL_PATTERN.search(inbound_text):
        reasons.append(HoldReasonCode.INBOUND_FINANCIAL_TRIGGER)
    if RSVP_PATTERN.search(inbound_text):
        reasons.append(HoldReasonCode.INBOUND_RSVP_TRIGGER)
    if PROMISE_PATTERN.search(inbound_text):
        reasons.append(HoldReasonCode.INBOUND_PROMISE_TRIGGER)

    if FINANCIAL_PATTERN.search(draft_text):
        reasons.append(HoldReasonCode.DRAFT_FINANCIAL_TRIGGER)
    if RSVP_PATTERN.search(draft_text):
        reasons.append(HoldReasonCode.DRAFT_RSVP_TRIGGER)
    if PROMISE_PATTERN.search(draft_text):
        reasons.append(HoldReasonCode.DRAFT_PROMISE_TRIGGER)
