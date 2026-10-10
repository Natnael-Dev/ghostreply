"""Inbound event data models and channel types."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Literal, Optional

ChannelType = Literal["wa", "tg"]
MediaType = Literal["audio", "image", "video", "document"]

VALID_CHANNELS = {"wa", "tg"}
VALID_MEDIA_TYPES = {"audio", "image", "video", "document"}
SAFETY_FLAGS = (
    "is_group",
    "is_forwarded",
    "is_quoted",
    "is_edited",
    "has_link_preview",
    "is_bot",
    "is_self",
)


class IntakeVerdict(str, Enum):
    """Triage verdict before passing to auto-send gate."""

    DROP = "DROP"
    PROCESS = "PROCESS"


@dataclass(frozen=True)
class InboundEvent:
    """Channel-agnostic normalized representation of an incoming message.

    Safety Invariant: All safety flags are REQUIRED with no default values
    to prevent accidental fail-open defaults in consumer adapters.
    """

    channel: ChannelType
    message_id: str
    sender_id: str
    chat_id: str
    timestamp: datetime
    text: Optional[str]
    media_type: Optional[MediaType]
    media_id: Optional[str]

    # Structural safety flags (REQUIRED - no defaults permitted)
    is_group: bool
    is_forwarded: bool
    is_quoted: bool
    is_edited: bool
    has_link_preview: bool
    is_bot: bool
    is_self: bool

    # Opaque transport diagnostics
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._validate_channel_and_namespaces()
        self._validate_safety_flags()

    def _validate_channel_and_namespaces(self) -> None:
        if self.channel not in VALID_CHANNELS:
            raise ValueError(f"Invalid channel: {self.channel}")

        expected_prefix = f"{self.channel}:"
        if not self.sender_id.startswith(expected_prefix):
            raise ValueError(
                f"sender_id must be prefixed with '{expected_prefix}', got '{self.sender_id}'"
            )
        if not self.chat_id.startswith(expected_prefix):
            raise ValueError(
                f"chat_id must be prefixed with '{expected_prefix}', got '{self.chat_id}'"
            )

        if self.media_type is not None and self.media_type not in VALID_MEDIA_TYPES:
            raise ValueError(f"Invalid media_type: {self.media_type}")

    def _validate_safety_flags(self) -> None:
        for flag_name in SAFETY_FLAGS:
            val = getattr(self, flag_name)
            if not isinstance(val, bool):
                raise TypeError(
                    f"Safety flag '{flag_name}' must be a strict bool, got {type(val).__name__}"
                )
