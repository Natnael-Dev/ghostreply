"""Abstract contracts and protocols for communication channel adapters."""
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol, runtime_checkable
from app.channels.events import ChannelType, InboundEvent


@dataclass(frozen=True)
class SendResult:
    """Outcome of a dispatch attempt across a channel."""

    success: bool
    channel_message_id: Optional[str]
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None


@dataclass(frozen=True)
class ContactProfile:
    """Channel-specific metadata and identity representation."""

    contact_id: str  # Namespaced identifier (e.g. "wa:+15550100000")
    display_name: Optional[str]
    handle_or_phone: Optional[str]


@runtime_checkable
class ChannelAdapter(Protocol):
    """Protocol implemented by communication adapters (WhatsApp, Telegram)."""

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
        handler: Callable[[InboundEvent], Awaitable[None]],
    ) -> None:
        """Register async callback for normalized inbound delivery."""
        ...

    def stream_inbound(self) -> AsyncIterator[InboundEvent]:
        """Yield inbound events as an asynchronous iterator."""
        ...
