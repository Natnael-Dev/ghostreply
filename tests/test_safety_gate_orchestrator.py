from datetime import datetime, timezone

from app.channels.events import InboundEvent
from app.gate.models import GateInput, HoldReasonCode, KnowledgeItem
from app.gate.orchestrator import evaluate_safety_gate


class MockClock:
    def __init__(self, t: datetime):
        self._t = t

    def now_utc(self) -> datetime:
        return self._t


def make_gate_input(
    text: str = "Hi, can you meet at 3pm?",
    draft: str = "I am free at 3pm",
    contact_mode: str = "auto_send",
    detected_language: str = "en",
    language_confidence: float = 0.95,
    has_geez_chars: bool = False,
    quoted_claims_verified: bool = True,
    entailment_verified: bool = True,
    entailment_commits_or_agrees: bool = False,
    is_claim_free_allowlisted: bool = True,
    needs_owner: bool = False,
    kill_switch_active: bool = False,
    shadow_mode_active: bool = False,
    rate_limits_clear: bool = True,
    timestamp: datetime = None,
) -> GateInput:
    event = InboundEvent(
        channel="wa",
        message_id="msg_1",
        sender_id="wa:+15550100000",
        chat_id="wa:+15550100000@c.us",
        timestamp=timestamp or datetime.now(timezone.utc),
        text=text,
        media_type=None,
        media_id=None,
        is_group=False,
        is_forwarded=False,
        is_quoted=False,
        is_edited=False,
        has_link_preview=False,
        is_bot=False,
        is_self=False,
    )
    return GateInput(
        event=event,
        draft_text=draft,
        contact_mode=contact_mode,
        retrieved_knowledge=[KnowledgeItem("about.md", "Free at 3pm")],
        detected_language=detected_language,
        language_confidence=language_confidence,
        has_geez_chars=has_geez_chars,
        quoted_claims_verified=quoted_claims_verified,
        entailment_verified=entailment_verified,
        entailment_commits_or_agrees=entailment_commits_or_agrees,
        is_claim_free_allowlisted=is_claim_free_allowlisted,
        needs_owner=needs_owner,
        kill_switch_active=kill_switch_active,
        shadow_mode_active=shadow_mode_active,
        rate_limits_clear=rate_limits_clear,
    )


def test_gate_never_outputs_send():
    """CRITICAL RULE: The gate MUST NEVER output SEND."""
    inp = make_gate_input()
    decision = evaluate_safety_gate(inp)
    assert decision.decision == "HOLD"
    assert len(decision.reason_codes) > 0


def test_missing_verifiers_trigger_verifier_not_run():
    inp = make_gate_input(entailment_verified=None)
    decision = evaluate_safety_gate(inp)
    assert decision.decision == "HOLD"
    assert HoldReasonCode.VERIFIER_NOT_RUN in decision.reason_codes


def test_geez_and_non_english_rejection():
    inp_geez = make_gate_input(has_geez_chars=True)
    decision = evaluate_safety_gate(inp_geez)
    assert HoldReasonCode.GEEZ_CHARACTERS_DETECTED in decision.reason_codes

    inp_non_en = make_gate_input(
        detected_language="fr", language_confidence=0.9
    )
    decision_fr = evaluate_safety_gate(inp_non_en)
    assert HoldReasonCode.LANGUAGE_NOT_CONFIDENT_ENGLISH in (
        decision_fr.reason_codes
    )


def test_entailment_and_claims_failures():
    inp_entail_fail = make_gate_input(entailment_verified=False)
    d1 = evaluate_safety_gate(inp_entail_fail)
    assert HoldReasonCode.ENTAILMENT_FAILED in d1.reason_codes

    inp_commits = make_gate_input(entailment_commits_or_agrees=True)
    d2 = evaluate_safety_gate(inp_commits)
    assert HoldReasonCode.ENTAILMENT_COMMITS_OR_AGREES in d2.reason_codes

    inp_quote_fail = make_gate_input(quoted_claims_verified=False)
    d3 = evaluate_safety_gate(inp_quote_fail)
    assert HoldReasonCode.QUOTED_SPAN_UNVERIFIED in d3.reason_codes

    inp_claim_free = make_gate_input(is_claim_free_allowlisted=False)
    d4 = evaluate_safety_gate(inp_claim_free)
    assert HoldReasonCode.CLAIM_FREE_NOT_ALLOWLISTED in d4.reason_codes


def test_operational_flags_triggers():
    inp_kill = make_gate_input(kill_switch_active=True)
    dec_kill = evaluate_safety_gate(inp_kill)
    assert HoldReasonCode.KILL_SWITCH_ENGAGED in dec_kill.reason_codes

    inp_shadow = make_gate_input(shadow_mode_active=True)
    dec_shadow = evaluate_safety_gate(inp_shadow)
    assert HoldReasonCode.SHADOW_MODE_ENABLED in dec_shadow.reason_codes

    inp_rate = make_gate_input(rate_limits_clear=False)
    dec_rate = evaluate_safety_gate(inp_rate)
    assert (
        HoldReasonCode.RATE_LIMIT_OR_COOLDOWN_EXCEEDED in dec_rate.reason_codes
    )

    inp_contact = make_gate_input(contact_mode="always_ask")
    dec_contact = evaluate_safety_gate(inp_contact)
    assert (
        HoldReasonCode.CONTACT_MODE_ASK_OR_IGNORE in dec_contact.reason_codes
    )
