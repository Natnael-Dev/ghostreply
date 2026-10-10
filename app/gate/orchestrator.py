"""Hold-Only Safety Gate Orchestrator (Phase 3)."""
from datetime import datetime, timezone
from typing import Optional

from app.gate.models import GateDecision, GateInput, HoldReasonCode
from app.gate.prefilter import Clock, SystemClock, evaluate_prefilters


def evaluate_safety_gate(
    gate_input: GateInput,
    clock: Optional[Clock] = None,
) -> GateDecision:
    """Evaluate pure conjunction safety gate.

    CRITICAL RULE:
    The gate MUST NEVER output SEND. It only outputs HOLD with a list
    of HoldReasonCodes. The system fails closed.
    """
    reasons: list[HoldReasonCode] = []

    # 1. Structural, Temporal, and Keyword Pre-Filters
    prefilter_reasons = evaluate_prefilters(
        gate_input.event,
        draft_text=gate_input.draft_text,
        clock=clock or SystemClock(),
    )
    reasons.extend(prefilter_reasons)

    # 2. Language and Character Invariants
    _check_language(gate_input, reasons)

    # 3. Grounding, Entailment, and Claim Verifiers
    _check_verifiers(gate_input, reasons)

    # 4. Operational and Configuration Controls
    _check_operational(gate_input, reasons)

    # Invariant: Gate strictly holds for human approval
    if not reasons:
        reasons.append(HoldReasonCode.CONTACT_MODE_ASK_OR_IGNORE)

    return GateDecision(
        decision="HOLD",
        reason_codes=reasons,
        evaluated_at=datetime.now(timezone.utc),
    )


def _check_language(
    inp: GateInput, reasons: list[HoldReasonCode]
) -> None:
    if inp.has_geez_chars:
        reasons.append(HoldReasonCode.GEEZ_CHARACTERS_DETECTED)
    if inp.detected_language != "en" or inp.language_confidence < 0.7:
        reasons.append(HoldReasonCode.LANGUAGE_NOT_CONFIDENT_ENGLISH)


def _check_verifiers(
    inp: GateInput, reasons: list[HoldReasonCode]
) -> None:
    verifier_flags = [
        inp.quoted_claims_verified,
        inp.entailment_verified,
        inp.entailment_commits_or_agrees,
        inp.is_claim_free_allowlisted,
    ]
    if any(flag is None for flag in verifier_flags):
        reasons.append(HoldReasonCode.VERIFIER_NOT_RUN)

    if inp.entailment_verified is False:
        reasons.append(HoldReasonCode.ENTAILMENT_FAILED)
    if inp.entailment_commits_or_agrees is True:
        reasons.append(HoldReasonCode.ENTAILMENT_COMMITS_OR_AGREES)
    if inp.quoted_claims_verified is False:
        reasons.append(HoldReasonCode.QUOTED_SPAN_UNVERIFIED)
    if inp.is_claim_free_allowlisted is False:
        reasons.append(HoldReasonCode.CLAIM_FREE_NOT_ALLOWLISTED)
    if inp.needs_owner:
        reasons.append(HoldReasonCode.GENERATION_FLAGGED_NEEDS_OWNER)


def _check_operational(
    inp: GateInput, reasons: list[HoldReasonCode]
) -> None:
    if inp.kill_switch_active:
        reasons.append(HoldReasonCode.KILL_SWITCH_ENGAGED)
    if inp.shadow_mode_active:
        reasons.append(HoldReasonCode.SHADOW_MODE_ENABLED)
    if not inp.rate_limits_clear:
        reasons.append(HoldReasonCode.RATE_LIMIT_OR_COOLDOWN_EXCEEDED)
    if inp.contact_mode != "auto_send":
        reasons.append(HoldReasonCode.CONTACT_MODE_ASK_OR_IGNORE)
