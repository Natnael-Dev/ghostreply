import pytest
from datetime import datetime, timezone
from app.channels.events import (
    InboundEvent,
    IntakeVerdict,
)
from app.channels.base import (
    ChannelAdapter,
    ContactProfile,
    SendResult,
)


def valid_event_kwargs():
    return {
        "channel": "wa",
        "message_id": "wa_msg_001",
        "sender_id": "wa:+15550100000",
        "chat_id": "wa:+15550100000@c.us",
        "timestamp": datetime.now(timezone.utc),
        "text": "Hello, world!",
        "media_type": None,
        "media_id": None,
        "is_group": False,
        "is_forwarded": False,
        "is_quoted": False,
        "is_edited": False,
        "has_link_preview": False,
        "is_bot": False,
        "is_self": False,
    }


def test_valid_inbound_event():
    kwargs = valid_event_kwargs()
    event = InboundEvent(**kwargs)
    assert event.channel == "wa"
    assert event.sender_id == "wa:+15550100000"
    assert event.is_bot is False
    assert event.is_self is False
    assert event.is_group is False


@pytest.mark.parametrize("missing_field", [
    "is_group",
    "is_forwarded",
    "is_quoted",
    "is_edited",
    "has_link_preview",
    "is_bot",
    "is_self",
])
def test_missing_safety_flags_raise_type_error(missing_field):
    kwargs = valid_event_kwargs()
    del kwargs[missing_field]
    with pytest.raises(TypeError):
        InboundEvent(**kwargs)


@pytest.mark.parametrize("bad_field,bad_value", [
    ("is_group", None),
    ("is_bot", "false"),
    ("is_self", 0),
    ("channel", "discord"),
    ("sender_id", "invalid_no_namespace"),
    ("chat_id", "invalid_no_namespace"),
])
def test_invalid_types_and_namespaces_raise_error(bad_field, bad_value):
    kwargs = valid_event_kwargs()
    kwargs[bad_field] = bad_value
    with pytest.raises((TypeError, ValueError)):
        InboundEvent(**kwargs)


def test_intake_verdict_enum():
    assert IntakeVerdict.DROP.value == "DROP"
    assert IntakeVerdict.PROCESS.value == "PROCESS"


def test_send_result_and_contact_profile():
    res = SendResult(success=True, channel_message_id="msg_99")
    assert res.success is True
    assert res.channel_message_id == "msg_99"

    profile = ContactProfile(
        contact_id="wa:+15550100000",
        display_name="Mom",
        handle_or_phone="+15550100000",
    )
    assert profile.contact_id == "wa:+15550100000"
    assert profile.display_name == "Mom"


def test_channel_adapter_protocol():
    class DummyAdapter:
        channel_name = "wa"

        async def start(self) -> None:
            pass

        async def stop(self) -> None:
            pass

        async def send_text(self, recipient_id: str, text: str):
            return SendResult(success=True, channel_message_id="1")

        async def get_contact_info(self, contact_id: str):
            return ContactProfile(
                contact_id=contact_id,
                display_name=None,
                handle_or_phone=None,
            )

        async def download_media(self, media_id: str) -> bytes:
            return b""

        def register_inbound_handler(self, handler) -> None:
            pass

        async def stream_inbound(self):
            if False:
                yield None

    adapter = DummyAdapter()
    assert isinstance(adapter, ChannelAdapter)
