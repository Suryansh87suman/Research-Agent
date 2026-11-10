"""
hypothesis_engine.py — Generate, refine, and evaluate research hypotheses using IBM Granite.

Capabilities:
- Generate novel hypotheses from a research question and background literature
- Score hypothesis plausibility
- Suggest experiments to test a hypothesis
- Draft a hypothesis section for a paper
"""

import logging
from typing import List

from research_agent.granite_client import GraniteClient
from research_agent.tools.literature_search import Paper

logger = logging.getLogger(__name__)

_SYSTEM_HYPOTHESIS = (
    "You are a senior scientist and research mentor powered by IBM Granite. "
    "Your role is to formulate rigorous, testable, and novel scientific hypotheses "
    "based on the current state of research. Hypotheses must be: specific, "
    "falsifiable, grounded in the literature, and clearly stated."
)

_SYSTEM_EXPERIMENT = (
    "You are an experimental design expert powered by IBM Granite. "
    "Propose concrete, feasible experiments or studies to test the given hypothesis. "
    "Include: study type, variables, data collection approach, and expected outcomes."
)

_SYSTEM_EVALUATE = (
    "You are a critical peer reviewer powered by IBM Granite. "
    "Evaluate the given hypothesis for: novelty, feasibility, scientific rigor, "
    "and alignment with the existing literature. Provide a score (1-10) and justification."
)


class HypothesisEngineTool:
    """
    Generates and evaluates research hypotheses using IBM Granite.

    Parameters
    ----------
    client : GraniteClient
    """

    def __init__(self, client: GraniteClient) -> None:
        self._client = client

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_hypotheses(
        self,
        research_question: str,
        papers: List[Paper],
        count: int = 3,
    ) -> List[str]:
        """
        Generate *count* hypotheses related to *research_question*.

        Parameters
        ----------
        research_question : str
        papers : list of Paper
            Background literature to inform the hypotheses.
        count : int
            Number of hypotheses to generate (1-5).

        Returns
        -------
        list of str
            Each item is one hypothesis statement.
        """
        count = max(1, min(count, 5))
        context = "\n".join(
            f"- {p.title} ({p.year or '?'}): {(p.abstract or '')[:300]}"
            for p in papers[:8]
        )
        user_msg = (
            f"Research question: {research_question}\n\n"
            f"Background literature:\n{context}\n\n"
            f"Generate {count} distinct, testable hypotheses. "
            f"Number each hypothesis (H1, H2, …). "
            f"Each hypothesis should be 1-2 sentences."
        )
        logger.info("Generating %d hypotheses for: '%s'", count, research_question[:60])
        raw = self._client.generate_with_system(
            _SYSTEM_HYPOTHESIS, user_msg, max_tokens=800
        )
        return self._parse_numbered_list(raw, count)

    def refine_hypothesis(self, hypothesis: str, feedback: str) -> str:
        """
        Refine an existing hypothesis based on feedback or critique.

        Parameters
        ----------
        hypothesis : str
            The original hypothesis statement.
        feedback : str
            Critique or suggested improvements.

        Returns
        -------
        str
            Refined hypothesis.
        """
        user_msg = (
            f"Original hypothesis:\n{hypothesis}\n\n"
            f"Feedback / critique:\n{feedback}\n\n"
            f"Rewrite the hypothesis addressing the feedback. "
            f"Keep it concise, specific, and testable."
        )
        return self._client.generate_with_system(
            _SYSTEM_HYPOTHESIS, user_msg, max_tokens=300
        )

    def suggest_experiments(self, hypothesis: str) -> str:
        """
        Suggest experimental approaches to test a hypothesis.

        Parameters
        ----------
        hypothesis : str
            The hypothesis to test.

        Returns
        -------
        str
            Structured experimental suggestions from Granite.
        """
        user_msg = (
            f"Hypothesis to test:\n{hypothesis}\n\n"
            f"Propose 2-3 concrete experimental designs or studies to test this hypothesis. "
            f"For each, specify: (1) study type, (2) key variables, "
            f"(3) data collection method, (4) expected outcome."
        )
        logger.info("Suggesting experiments for hypothesis.")
        return self._client.generate_with_system(
            _SYSTEM_EXPERIMENT, user_msg, max_tokens=700
        )

    def evaluate_hypothesis(self, hypothesis: str, papers: List[Paper]) -> str:
        """
        Critically evaluate a hypothesis against the literature.

        Parameters
        ----------
        hypothesis : str
        papers : list of Paper
            Relevant background papers.

        Returns
        -------
        str
            Evaluation with a plausibility score (1-10).
        """
        context = "\n".join(
            f"- {p.title} ({p.year or '?'}): {(p.abstract or '')[:200]}"
            for p in papers[:6]
        )
        user_msg = (
            f"Hypothesis:\n{hypothesis}\n\n"
            f"Relevant literature:\n{context}\n\n"
            f"Evaluate this hypothesis. Provide:\n"
            f"1. Novelty assessment\n"
            f"2. Feasibility\n"
            f"3. Scientific rigor\n"
            f"4. Alignment with literature\n"
            f"5. Overall plausibility score (1-10) with justification."
        )
        logger.info("Evaluating hypothesis.")
        return self._client.generate_with_system(
            _SYSTEM_EVALUATE, user_msg, max_tokens=600
        )

    def draft_hypothesis_section(
        self, research_question: str, hypotheses: List[str]
    ) -> str:
        """
        Draft a formal 'Hypothesis' section for a research paper.

        Parameters
        ----------
        research_question : str
        hypotheses : list of str
            The hypotheses to include.

        Returns
        -------
        str
            A formal, academic hypothesis section in Markdown.
        """
        hyp_text = "\n".join(f"{i+1}. {h}" for i, h in enumerate(hypotheses))
        user_msg = (
            f"Research question: {research_question}\n\n"
            f"Hypotheses:\n{hyp_text}\n\n"
            f"Write a formal 'Hypotheses' section for a research paper. "
            f"Introduce each hypothesis in academic prose, explain its rationale, "
            f"and note what evidence would support or refute it."
        )
        return self._client.generate_with_system(
            _SYSTEM_HYPOTHESIS, user_msg, max_tokens=900
        )

    # ── Helper ────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_numbered_list(text: str, expected: int) -> List[str]:
        """Parse a numbered list from Granite output into individual items."""
        import re
        items = re.split(r"\n(?=H?\d+[.)]\s)", text.strip())
        cleaned = [re.sub(r"^H?\d+[.)]\s*", "", item).strip() for item in items if item.strip()]
        if not cleaned:
            # Fallback: return the whole text as one item
            return [text.strip()]
        return cleaned[:expected]
