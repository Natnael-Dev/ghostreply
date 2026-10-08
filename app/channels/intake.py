"""Pre-gate intake evaluation and triage routing."""
from typing import Optional

from app.channels.events import InboundEvent, IntakeVerdict
from app.channels.ledger import InboundLedger


def evaluate_intake_verdict(event: InboundEvent) -> IntakeVerdict:
    """Evaluate pre-gate intake routing for an incoming event.

    Triage Invariant (CONTRACTS.md Sec 1.2):
    - If event.is_group == True OR event.is_bot == True
      OR event.is_self == True:
      verdict is IntakeVerdict.DROP.
    - Otherwise:
      verdict is IntakeVerdict.PROCESS.
    """
    if event.is_group or event.is_bot or event.is_self:
        return IntakeVerdict.DROP
    return IntakeVerdict.PROCESS


class IntakeRouter:
    """Pre-gate router combining triage evaluation with idempotency ledger."""

    def __init__(self, ledger: Optional[InboundLedger] = None) -> None:
        self.ledger = ledger

    def evaluate(self, event: InboundEvent) -> IntakeVerdict:
        """Pure intake triage check."""
        return evaluate_intake_verdict(event)

    async def intake(self, event: InboundEvent) -> IntakeVerdict:
        """Evaluate triage verdict and atomically claim message if eligible."""
        verdict = self.evaluate(event)
        if verdict == IntakeVerdict.DROP:
            return IntakeVerdict.DROP

        if self.ledger is not None:
            claimed = await self.ledger.claim(event.channel, event.message_id)
            if not claimed:
                return IntakeVerdict.DROP

        return IntakeVerdict.PROCESS
