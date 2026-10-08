import pytest
from unittest.mock import AsyncMock, patch
from app.channels.base import ChannelAdapter
from app.channels.whatsapp import WhatsAppAdapter


@pytest.fixture
def wa_adapter():
    return WhatsAppAdapter(
        bridge_url="http://127.0.0.1:3001",
        bridge_token="secret_token",
    )


def test_whatsapp_adapter_implements_protocol(wa_adapter):
    assert isinstance(wa_adapter, ChannelAdapter)
    assert wa_adapter.channel_name == "wa"


def test_translate_raw_event_direct_message(wa_adapter):
    raw = {
        "from": "+15550100000@c.us",
        "body": "Hello from WA",
        "id": "wa_msg_123",
        "timestamp": 1700000000,
        "type": "text",
    }
    event = wa_adapter.translate_raw_event(raw)
    assert event.channel == "wa"
    assert event.message_id == "wa_msg_123"
    assert event.sender_id == "wa:+15550100000"
    assert event.chat_id == "wa:+15550100000@c.us"
    assert event.text == "Hello from WA"
    assert event.is_group is False
    assert event.is_bot is False
    assert event.is_self is False
    assert event.is_forwarded is False
    assert event.is_quoted is False
    assert event.is_edited is False
    assert event.has_link_preview is False


def test_translate_raw_event_group_and_self(wa_adapter):
    raw_group = {
        "from": "12345678@g.us",
        "body": "Group chatter",
        "from_me": False,
    }
    event = wa_adapter.translate_raw_event(raw_group)
    assert event.is_group is True
    assert event.is_self is False

    raw_self = {
        "from": "+15550100000@c.us",
        "body": "Self message",
        "from_me": True,
    }
    event_self = wa_adapter.translate_raw_event(raw_self)
    assert event_self.is_self is True


def test_translate_raw_event_voice_media(wa_adapter):
    raw_voice = {
        "from": "+15550100000@c.us",
        "body": "",
        "type": "voice",
        "media_base64": "UklGRiQAAABXQVZFZmt0",
    }
    event = wa_adapter.translate_raw_event(raw_voice)
    assert event.media_type == "audio"


@pytest.mark.anyio
async def test_send_text_success(wa_adapter):
    from unittest.mock import MagicMock
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"success": true}'
    mock_resp.json.return_value = {"success": True, "id": "wa_sent_99"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = await wa_adapter.send_text("wa:+15550100000@c.us", "Hello back")
        assert res.success is True
        assert res.channel_message_id == "wa_sent_99"


@pytest.mark.anyio
async def test_inbound_handler_and_streaming(wa_adapter):
    received = []

    async def sample_handler(event):
        received.append(event)

    wa_adapter.register_inbound_handler(sample_handler)

    raw = {
        "from": "+15550100000@c.us",
        "body": "Streaming test",
    }
    await wa_adapter.handle_raw_event(raw)

    assert len(received) == 1
    assert received[0].text == "Streaming test"
