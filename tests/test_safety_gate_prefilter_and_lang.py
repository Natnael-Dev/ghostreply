import pytest
from datetime import datetime, timezone, timedelta
from app.channels.events import InboundEvent
from app.gate.models import HoldReasonCode
from app.gate.prefilter import evaluate_prefilters
from app.gate.language import detect_language


def make_event(
    text="Hey there, how are you doing today?",
    timestamp=None,
    is_forwarded=False,
    is_quoted=False,
    is_edited=False,
    has_link_preview=False,
    media_type=None,
    media_id=None,
):
    return InboundEvent(
        channel="wa",
        message_id="msg_gate_1",
        sender_id="wa:+15550100000",
        chat_id="wa:+15550100000@c.us",
        timestamp=timestamp or datetime.now(timezone.utc),
        text=text,
        media_type=media_type,
        media_id=media_id,
        is_group=False,
        is_forwarded=is_forwarded,
        is_quoted=is_quoted,
        is_edited=is_edited,
        has_link_preview=has_link_preview,
        is_bot=False,
        is_self=False,
    )


class MockClock:
    def __init__(self, current_time: datetime):
        self._now = current_time

    def now_utc(self) -> datetime:
        return self._now


def test_stale_message_detection():
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(seconds=301)
    clock = MockClock(now)

    stale_event = make_event(timestamp=old_time)
    reasons = evaluate_prefilters(stale_event, "draft", clock=clock)
    assert HoldReasonCode.MESSAGE_STALE in reasons

    fresh_event = make_event(timestamp=now - timedelta(seconds=60))
    reasons_fresh = evaluate_prefilters(fresh_event, "draft", clock=clock)
    assert HoldReasonCode.MESSAGE_STALE not in reasons_fresh


@pytest.mark.parametrize("flag,expected_reason", [
    ({"is_forwarded": True}, HoldReasonCode.FORWARDED_MESSAGE),
    ({"is_quoted": True}, HoldReasonCode.QUOTED_MESSAGE),
    ({"is_edited": True}, HoldReasonCode.EDITED_MESSAGE),
    ({"has_link_preview": True}, HoldReasonCode.LINK_PREVIEW_DETECTED),
    (
        {"media_type": "audio", "media_id": "b64"},
        HoldReasonCode.MEDIA_ATTACHMENT_HELD,
    ),
])
def test_structural_triggers(flag, expected_reason):
    event = make_event(**flag)
    reasons = evaluate_prefilters(event, "draft text")
    assert expected_reason in reasons


def test_keyword_triggers():
    event_fin = make_event(text="Please wire $500 to my account")
    reasons = evaluate_prefilters(event_fin, "okay")
    assert HoldReasonCode.INBOUND_FINANCIAL_TRIGGER in reasons

    event_rsvp = make_event(text="Will you attend the RSVP dinner?")
    reasons = evaluate_prefilters(event_rsvp, "I will be there")
    assert HoldReasonCode.INBOUND_RSVP_TRIGGER in reasons

    event_clean = make_event(text="What time is lunch?")
    reasons_draft_promise = evaluate_prefilters(
        event_clean, "I promise I will definitely come"
    )
    assert HoldReasonCode.DRAFT_PROMISE_TRIGGER in reasons_draft_promise


def test_geez_character_detection():
    # Amharic / Ge'ez characters range \u1200 - \u137F
    geez_text = "ሰላም እንደምን አለህ"
    lang, conf, has_geez = detect_language(geez_text)
    assert has_geez is True
    assert lang != "en"


def test_short_english_edge_cases():
    words = [
        "ok", "k", "sure", "thanks", "yes", "cool", "see you", "will do"
    ]
    for word in words:
        lang, conf, has_geez = detect_language(word)
        assert has_geez is False
        assert lang == "en"
        assert conf >= 0.8
