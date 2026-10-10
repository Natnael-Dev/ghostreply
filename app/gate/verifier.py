"""Claim verifier and entailment interfaces and evaluation."""
from typing import Optional, Protocol, Tuple


class LLMClient(Protocol):
    """Mockable LLM completion and judge interface."""

    async def generate_reply(
        self,
        inbound_text: str,
        system_prompt: str,
        context_items: list[str],
    ) -> str:
        ...

    async def judge_entailment(
        self,
        draft_text: str,
        context_text: str,
    ) -> Tuple[bool, bool]:
        """Returns (logically_entailed, commits_or_agrees)."""
        ...


class VerifierEvaluator:
    """Verifies grounding claims and entailment judgments."""

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self.llm_client = llm_client

    async def evaluate_claims(
        self,
        draft_text: str,
        context_text: str,
    ) -> Tuple[Optional[bool], Optional[bool]]:
        """Judge entailment and agreement commitment.

        Fails closed (returns None, None) if client is not provided or throws.
        """
        if self.llm_client is None:
            return None, None
        try:
            return await self.llm_client.judge_entailment(
                draft_text, context_text
            )
        except Exception:
            return None, None
