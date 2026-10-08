"""Inbound event data model and intake verdict contracts."""
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
        self._validate_media()

    def _validate_channel_and_namespaces(self) -> None:
        if self.channel not in VALID_CHANNELS:
            raise ValueError(f"Invalid channel: {self.channel}")
        expected_prefix = f"{self.channel}:"
        if not self.sender_id.startswith(expected_prefix):
            raise ValueError(
                f"sender_id '{self.sender_id}' must start with "
                f"'{expected_prefix}'"
            )
        if not self.chat_id.startswith(expected_prefix):
            raise ValueError(
                f"chat_id '{self.chat_id}' must start with "
                f"'{expected_prefix}'"
            )

    def _validate_safety_flags(self) -> None:
        for flag_name in SAFETY_FLAGS:
            val = getattr(self, flag_name)
            # bool is a subclass of int in Python; ensure type(val) is bool
            if not isinstance(val, bool) or type(val) is not bool:
                raise TypeError(
                    f"Safety flag '{flag_name}' must be a strict bool, "
                    f"got {type(val).__name__}: {val}"
                )

    def _validate_media(self) -> None:
        if self.media_type and self.media_type not in VALID_MEDIA_TYPES:
            raise ValueError(f"Invalid media_type: {self.media_type}")
