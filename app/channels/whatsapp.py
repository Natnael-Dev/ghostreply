"""Concrete WhatsApp channel adapter integrating with Node bridge."""
import asyncio
import hashlib
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app import contacts
from app.channels.base import ContactProfile, SendResult
from app.channels.events import ChannelType, InboundEvent, MediaType


class WhatsAppAdapter:
    """Adapter wrapping WhatsApp web bridge into the ChannelAdapter seam."""

    channel_name: ChannelType = "wa"

    def __init__(
        self,
        bridge_url: Optional[str] = None,
        bridge_token: Optional[str] = None,
    ) -> None:
        self.bridge_url = (
            bridge_url or os.getenv("BRIDGE_API_URL", "http://127.0.0.1:3001")
        ).rstrip("/")
        self.bridge_token = (
            bridge_token if bridge_token is not None
            else os.getenv("BRIDGE_API_TOKEN", "")
        )
        self._handlers: list[Callable[[InboundEvent], Awaitable[None]]] = []
        self._queue: asyncio.Queue[InboundEvent] = asyncio.Queue()
        self._running = False

    async def start(self) -> None:
        """Start adapter listener state."""
        self._running = True

    async def stop(self) -> None:
        """Gracefully stop adapter."""
        self._running = False

    def register_inbound_handler(
        self,
        handler: Callable[[InboundEvent], Awaitable[None]],
    ) -> None:
        """Register asynchronous callback for inbound delivery."""
        self._handlers.append(handler)

    async def stream_inbound(self) -> AsyncIterator[InboundEvent]:
        """Yield inbound events asynchronously."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                yield event
            except asyncio.TimeoutError:
                continue

    async def handle_raw_event(self, raw: dict[str, Any]) -> InboundEvent:
        """Translate raw bridge dictionary and dispatch to handlers/queue."""
        event = self.translate_raw_event(raw)
        await self._queue.put(event)
        for handler in self._handlers:
            await handler(event)
        return event

    def translate_raw_event(self, raw: dict[str, Any]) -> InboundEvent:
        """Translate raw bridge JSON into a normalized InboundEvent."""
        from_id = str(raw.get("from") or raw.get("sender_id") or "")
        number = str(raw.get("number") or from_id.split("@")[0])
        sender_id = contacts.namespace_id("wa", number)
        chat_id = contacts.namespace_id("wa", from_id)

        msg_id = self._extract_message_id(raw, from_id)
        media_type = self._determine_media_type(str(raw.get("type", "text")))
        ts = self._parse_timestamp(raw.get("timestamp"))

        return InboundEvent(
            channel="wa",
            message_id=msg_id,
            sender_id=sender_id,
            chat_id=chat_id,
            timestamp=ts,
            text=raw.get("body") or raw.get("text"),
            media_type=media_type,
            media_id=raw.get("media_id") or raw.get("media_base64"),
            is_group=from_id.endswith("@g.us"),
            is_forwarded=bool(raw.get("is_forwarded", False)),
            is_quoted=bool(raw.get("is_quoted", False)),
            is_edited=bool(raw.get("is_edited", False)),
            has_link_preview=bool(raw.get("has_link_preview", False)),
            is_bot=bool(raw.get("is_bot", False)),
            is_self=bool(
                raw.get("from_me", False) or raw.get("is_self", False)
            ),
            raw_metadata=dict(raw),
        )

    def _extract_message_id(self, raw: dict[str, Any], from_id: str) -> str:
        if raw.get("id"):
            return str(raw["id"])
        if raw.get("message_id"):
            return str(raw["message_id"])
        h = hashlib.sha256(
            f"{from_id}:{raw.get('body', '')}:{time.time()}".encode()
        ).hexdigest()[:12]
        return f"wa_gen_{h}"

    def _determine_media_type(self, raw_type: str) -> Optional[MediaType]:
        mapping: dict[str, MediaType] = {
            "audio": "audio",
            "voice": "audio",
            "ptt": "audio",
            "image": "image",
            "video": "video",
            "document": "document",
        }
        return mapping.get(raw_type)

    def _parse_timestamp(self, raw_ts: Any) -> datetime:
        if isinstance(raw_ts, (int, float)):
            return datetime.fromtimestamp(raw_ts, tz=timezone.utc)
        return datetime.now(timezone.utc)

    async def send_text(self, recipient_id: str, text: str) -> SendResult:
        """Transmit plaintext message via the local Node WhatsApp bridge."""
        chat_id = contacts.strip_namespace(recipient_id)
        url = f"{self.bridge_url}/send-reply"
        headers = {"x-bridge-token": self.bridge_token}
        payload = {"chat_id": chat_id, "text": text}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json() if res.content else {}
                    msg_id = (
                        data.get("id") or data.get("message_id") or "wa_sent"
                    )
                    return SendResult(
                        success=True,
                        channel_message_id=msg_id,
                        sent_at=datetime.now(timezone.utc),
                    )
                err = f"Bridge HTTP {res.status_code}: {res.text[:120]}"
                return SendResult(
                    success=False,
                    channel_message_id=None,
                    error_message=err,
                )
        except Exception as exc:
            return SendResult(
                success=False,
                channel_message_id=None,
                error_message=str(exc),
            )

    async def get_contact_info(self, contact_id: str) -> ContactProfile:
        """Fetch contact profile using contacts lookup."""
        name = contacts.name_for(contact_id)
        raw = contacts.strip_namespace(contact_id)
        return ContactProfile(
            contact_id=contacts.namespace_id("wa", raw),
            display_name=name,
            handle_or_phone=raw.split("@")[0],
        )

    async def download_media(self, media_id: str) -> bytes:
        """Return binary content for media pointer."""
        import base64
        return base64.b64decode(media_id)
