"""Channel adapter interfaces and transport implementations."""
from app.channels.base import ChannelAdapter, ContactProfile, SendResult
from app.channels.events import (
    ChannelType,
    InboundEvent,
    IntakeVerdict,
    MediaType,
)
from app.channels.dispatcher import DispatchResult, dispatch_with_rechecks
from app.channels.intake import IntakeRouter, evaluate_intake_verdict
from app.channels.ledger import InboundLedger, SqliteInboundLedger
from app.channels.rate_limiter import RateLimiter, SqliteRateLimiter
from app.channels.whatsapp import WhatsAppAdapter

__all__ = [
    "ChannelAdapter",
    "ChannelType",
    "ContactProfile",
    "DispatchResult",
    "InboundEvent",
    "InboundLedger",
    "IntakeRouter",
    "IntakeVerdict",
    "MediaType",
    "RateLimiter",
    "SendResult",
    "SqliteInboundLedger",
    "SqliteRateLimiter",
    "WhatsAppAdapter",
    "dispatch_with_rechecks",
    "evaluate_intake_verdict",
]
