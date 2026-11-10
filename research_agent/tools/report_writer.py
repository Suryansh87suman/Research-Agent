"""
report_writer.py — Generate structured research reports using IBM Granite.

A report contains:
  1. Executive Summary
  2. Introduction & Background
  3. Literature Review (per paper)
  4. Synthesis & Themes
  5. Research Gaps
  6. Conclusion
  7. References
"""

import logging
from datetime import date
from pathlib import Path
from typing import List, Optional

from research_agent import config
from research_agent.granite_client import GraniteClient
from research_agent.tools.literature_search import Paper
from research_agent.tools.citation_manager import CitationManagerTool

logger = logging.getLogger(__name__)

_SYSTEM_REPORT = (
    "You are an expert academic writer and research analyst powered by IBM Granite. "
    "Write clear, precise, and well-structured academic content. "
    "Use formal language appropriate for a scientific report. "
    "Do not fabricate citations; only use the information provided."
)


class ReportWriterTool:
    """
    Generates a full research report in Markdown format using IBM Granite.

    Parameters
    ----------
    client : GraniteClient
    citation_manager : CitationManagerTool
    """

    def __init__(
        self,
        client: GraniteClient,
        citation_manager: CitationManagerTool,
    ) -> None:
        self._client = client
        self._citations = citation_manager

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_report(
        self,
        research_question: str,
        papers: List[Paper],
        title: Optional[str] = None,
        author: str = "Research Agent (IBM Granite)",
    ) -> str:
        """
        Generate a full Markdown research report.

        Parameters
        ----------
        research_question : str
            The central research question or topic.
        papers : list of Paper
            Papers retrieved and to be synthesised.
        title : str, optional
            Report title. If omitted, Granite will generate one.
        author : str
            Author line for the report header.

        Returns
        -------
        str
            The full report as a Markdown string.
        """
        if not title:
            title = self._generate_title(research_question)

        # Add papers to citation manager
        keys = self._citations.add_papers(papers)

        sections = []

        # Header
        sections.append(
            f"# {title}\n\n"
            f"**Author:** {author}  \n"
            f"**Date:** {date.today().isoformat()}  \n"
            f"**Powered by:** IBM Granite on IBM Cloud Lite  \n"
            f"**Research Question:** {research_question}\n"
        )

        # 1. Executive Summary
        logger.info("Generating executive summary …")
        sections.append(
            "## 1. Executive Summary\n\n"
            + self._generate_executive_summary(research_question, papers)
        )

        # 2. Introduction
        logger.info("Generating introduction …")
        sections.append(
            "## 2. Introduction & Background\n\n"
            + self._generate_introduction(research_question)
        )

        # 3. Literature Review
        logger.info("Generating literature review for %d papers …", len(papers))
        sections.append("## 3. Literature Review\n")
        for i, (key, paper) in enumerate(zip(keys, papers), start=1):
            sections.append(
                f"### 3.{i}. {paper.title}\n\n"
                + self._generate_paper_review(paper, key)
                + "\n"
            )

        # 4. Synthesis
        logger.info("Generating synthesis …")
        sections.append(
            "## 4. Synthesis & Emerging Themes\n\n"
            + self._generate_synthesis(research_question, papers)
        )

        # 5. Research Gaps
        logger.info("Identifying research gaps …")
        sections.append(
            "## 5. Research Gaps & Future Directions\n\n"
            + self._generate_gaps(research_question, papers)
        )

        # 6. Conclusion
        logger.info("Generating conclusion …")
        sections.append(
            "## 6. Conclusion\n\n"
            + self._generate_conclusion(research_question, papers)
        )

        # 7. References
        sections.append(
            "## 7. References\n\n"
            + self._citations.get_formatted_list(fmt="apa")
        )

        report = "\n\n---\n\n".join(sections)
        logger.info("Report generation complete (%d characters).", len(report))
        return report

    def save_report(self, report: str, filename: Optional[str] = None) -> Path:
        """Save the Markdown report to disk. Returns the file path."""
        filename = filename or f"research_report_{date.today().isoformat()}.md"
        out_path = config.OUTPUT_DIR / filename
        out_path.write_text(report, encoding="utf-8")
        logger.info("Report saved to %s", out_path)
        return out_path

    # ── Section generators ────────────────────────────────────────────────────

    def _generate_title(self, research_question: str) -> str:
        prompt = (
            f"Generate a concise, academic-style report title for the following "
            f"research question. Return ONLY the title, nothing else.\n\n"
            f"Research question: {research_question}"
        )
        return self._client.generate_with_system(_SYSTEM_REPORT, prompt, max_tokens=80)

    def _generate_executive_summary(
        self, research_question: str, papers: List[Paper]
    ) -> str:
        paper_titles = "\n".join(f"- {p.title}" for p in papers[:10])
        prompt = (
            f"Write a 150-200 word executive summary for a literature review report "
            f"on the following research question:\n\n"
            f"**Research question:** {research_question}\n\n"
            f"**Papers reviewed:**\n{paper_titles}\n\n"
            f"The summary should overview the scope, key themes, and main conclusions."
        )
        return self._client.generate_with_system(_SYSTEM_REPORT, prompt, max_tokens=400)

    def _generate_introduction(self, research_question: str) -> str:
        prompt = (
            f"Write a 200-250 word academic introduction for a literature review on:\n\n"
            f"{research_question}\n\n"
            f"Cover: background context, why this topic is important, and the "
            f"scope of this review."
        )
        return self._client.generate_with_system(_SYSTEM_REPORT, prompt, max_tokens=500)

    def _generate_paper_review(self, paper: Paper, key: str) -> str:
        abstract = (paper.abstract or "No abstract available.")[:800]
        prompt = (
            f"Write a 100-150 word academic paragraph reviewing the following paper "
            f"for inclusion in a literature review. Mention the research problem, "
            f"methodology, and key findings. End with the citation key [{key}].\n\n"
            f"Title: {paper.title}\n"
            f"Authors: {', '.join(paper.authors[:4])}\n"
            f"Year: {paper.year or 'Unknown'}\n"
            f"Abstract: {abstract}"
        )
        return self._client.generate_with_system(_SYSTEM_REPORT, prompt, max_tokens=350)

    def _generate_synthesis(
        self, research_question: str, papers: List[Paper]
    ) -> str:
        summaries = "\n\n".join(
            f"**{p.title}** ({p.year or '?'}): {(p.abstract or '')[:300]}"
            for p in papers[:8]
        )
        prompt = (
            f"Based on the following papers related to '{research_question}', "
            f"write a 200-300 word synthesis identifying: (1) common themes, "
            f"(2) agreements across papers, (3) methodological trends.\n\n"
            f"{summaries}"
        )
        return self._client.generate_with_system(_SYSTEM_REPORT, prompt, max_tokens=600)

    def _generate_gaps(self, research_question: str, papers: List[Paper]) -> str:
        summaries = "\n".join(
            f"- {p.title} ({p.year or '?'})"
            for p in papers[:10]
        )
        prompt = (
            f"Given the following papers on '{research_question}', identify "
            f"3-5 research gaps and suggest future research directions. "
            f"Be specific and grounded in the literature provided.\n\n"
            f"Papers:\n{summaries}"
        )
        return self._client.generate_with_system(_SYSTEM_REPORT, prompt, max_tokens=600)

    def _generate_conclusion(
        self, research_question: str, papers: List[Paper]
    ) -> str:
        prompt = (
            f"Write a 150-200 word academic conclusion for a literature review "
            f"on '{research_question}' that reviewed {len(papers)} papers. "
            f"Summarise the overall state of research and what future work is needed."
        )
        return self._client.generate_with_system(_SYSTEM_REPORT, prompt, max_tokens=400)
