"""Channel adapter interfaces and transport implementations."""
from app.channels.base import ChannelAdapter, ContactProfile, SendResult
from app.channels.events import (
    ChannelType,
    InboundEvent,
    IntakeVerdict,
    MediaType,
)
from app.channels.intake import IntakeRouter, evaluate_intake_verdict
from app.channels.ledger import InboundLedger, SqliteInboundLedger
from app.channels.whatsapp import WhatsAppAdapter

__all__ = [
    "ChannelAdapter",
    "ChannelType",
    "ContactProfile",
    "InboundEvent",
    "InboundLedger",
    "IntakeRouter",
    "IntakeVerdict",
    "MediaType",
    "SendResult",
    "SqliteInboundLedger",
    "WhatsAppAdapter",
    "evaluate_intake_verdict",
]
