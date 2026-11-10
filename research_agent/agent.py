"""
agent.py — ResearchAgent: top-level orchestrator.

The ResearchAgent provides a high-level API that chains all tools together:
  - search() → literature_search
  - summarise() → summarizer
  - add_citations() → citation_manager
  - hypothesise() → hypothesis_engine
  - write_report() → report_writer

It also provides run_pipeline() which executes the full research workflow
from a single research question.
"""

import logging
from pathlib import Path
from typing import List, Optional

from research_agent.granite_client import GraniteClient
from research_agent.tools.literature_search import LiteratureSearchTool, Paper
from research_agent.tools.summarizer import SummarizerTool
from research_agent.tools.citation_manager import CitationManagerTool
from research_agent.tools.report_writer import ReportWriterTool
from research_agent.tools.hypothesis_engine import HypothesisEngineTool
from research_agent import config

logger = logging.getLogger(__name__)


class ResearchAgent:
    """
    IBM Granite-powered Research Agent.

    Orchestrates literature search, summarisation, citation management,
    hypothesis generation, and automated report writing.

    Parameters
    ----------
    verbose : bool
        If True, print progress to stdout in addition to logging.

    Example
    -------
    >>> agent = ResearchAgent()
    >>> results = agent.run_pipeline("transformer models in drug discovery")
    >>> print(results["report_path"])
    """

    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose
        self._log("Initialising Research Agent (IBM Granite) …")

        self.granite = GraniteClient()
        self.search_tool = LiteratureSearchTool()
        self.summarizer = SummarizerTool(self.granite)
        self.citations = CitationManagerTool()
        self.report_writer = ReportWriterTool(self.granite, self.citations)
        self.hypothesis_engine = HypothesisEngineTool(self.granite)

        self._log(f"Research Agent ready. Output directory: {config.OUTPUT_DIR}")

    # ── High-level pipeline ───────────────────────────────────────────────────

    def run_pipeline(
        self,
        research_question: str,
        sources: Optional[List[str]] = None,
        num_hypotheses: int = 3,
        report_filename: Optional[str] = None,
    ) -> dict:
        """
        Run the complete research pipeline for a given research question.

        Steps
        -----
        1. Search literature (arXiv, Semantic Scholar, CrossRef)
        2. Summarise each retrieved paper
        3. Generate hypotheses grounded in the literature
        4. Write a full research report
        5. Export references in BibTeX and APA formats

        Parameters
        ----------
        research_question : str
            The research question or topic to investigate.
        sources : list of str, optional
            Which sources to query. Default: all three.
        num_hypotheses : int
            How many hypotheses to generate (1-5).
        report_filename : str, optional
            Filename for the saved Markdown report.

        Returns
        -------
        dict with keys:
            papers          — list[Paper]
            summaries       — dict[paper_title -> summary]
            hypotheses      — list[str]
            report_path     — Path
            bibtex_path     — Path
            apa_path        — Path
        """
        self._log(f"\n{'='*60}")
        self._log(f"Research Question: {research_question}")
        self._log(f"{'='*60}\n")

        # Step 1 — Literature search
        self._log("Step 1/5 — Searching literature …")
        papers = self.search(research_question, sources=sources)
        self._log(f"          Found {len(papers)} papers.\n")

        if not papers:
            logger.warning("No papers found. Aborting pipeline.")
            return {"error": "No papers found for the given query."}

        # Step 2 — Summarise papers
        self._log("Step 2/5 — Summarising papers …")
        summaries = {}
        for paper in papers:
            summary = self.summarize_paper(paper)
            summaries[paper.title] = summary
            self._log(f"          ✓ {paper.title[:70]}")
        self._log("")

        # Step 3 — Generate hypotheses
        self._log(f"Step 3/5 — Generating {num_hypotheses} hypotheses …")
        hypotheses = self.generate_hypotheses(
            research_question, papers, count=num_hypotheses
        )
        for i, h in enumerate(hypotheses, 1):
            self._log(f"          H{i}: {h[:100]}")
        self._log("")

        # Step 4 — Write report
        self._log("Step 4/5 — Writing research report …")
        report = self.report_writer.generate_report(
            research_question=research_question,
            papers=papers,
        )
        report_path = self.report_writer.save_report(report, filename=report_filename)
        self._log(f"          Report saved → {report_path}\n")

        # Step 5 — Export citations
        self._log("Step 5/5 — Exporting citations …")
        bibtex_path = self.citations.export_bibtex()
        apa_path = self.citations.export_apa()
        self.citations.export_json()
        self._log(f"          BibTeX → {bibtex_path}")
        self._log(f"          APA    → {apa_path}")
        self._log(f"\n{'='*60}")
        self._log("Pipeline complete.")
        self._log(f"{'='*60}\n")

        return {
            "papers": papers,
            "summaries": summaries,
            "hypotheses": hypotheses,
            "report_path": report_path,
            "bibtex_path": bibtex_path,
            "apa_path": apa_path,
        }

    # ── Individual tool wrappers ──────────────────────────────────────────────

    def search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
    ) -> List[Paper]:
        """Search academic literature and return a list of Paper objects."""
        return self.search_tool.search(query, sources=sources)

    def summarize_paper(self, paper: Paper, detailed: bool = False) -> str:
        """Summarise a single paper using IBM Granite."""
        return self.summarizer.summarise_paper(paper, detailed=detailed)

    def summarize_text(self, text: str) -> str:
        """Summarise arbitrary text using IBM Granite."""
        return self.summarizer.summarise_text(text)

    def extract_findings(self, paper: Paper) -> str:
        """Extract key findings from a paper."""
        return self.summarizer.extract_key_findings(paper)

    def compare_papers(self, papers: List[Paper]) -> str:
        """Generate a comparative analysis of multiple papers."""
        return self.summarizer.compare_papers(papers)

    def generate_hypotheses(
        self,
        research_question: str,
        papers: List[Paper],
        count: int = 3,
    ) -> List[str]:
        """Generate testable research hypotheses using IBM Granite."""
        return self.hypothesis_engine.generate_hypotheses(
            research_question, papers, count=count
        )

    def evaluate_hypothesis(self, hypothesis: str, papers: List[Paper]) -> str:
        """Evaluate a hypothesis against the literature."""
        return self.hypothesis_engine.evaluate_hypothesis(hypothesis, papers)

    def suggest_experiments(self, hypothesis: str) -> str:
        """Suggest experiments to test a hypothesis."""
        return self.hypothesis_engine.suggest_experiments(hypothesis)

    def add_citations(self, papers: List[Paper]) -> List[str]:
        """Add papers to the citation library. Returns citation keys."""
        return self.citations.add_papers(papers)

    def export_citations(self, fmt: str = "bibtex") -> Path:
        """Export citations. fmt: 'bibtex' | 'apa' | 'json'."""
        if fmt == "bibtex":
            return self.citations.export_bibtex()
        if fmt == "apa":
            return self.citations.export_apa()
        return self.citations.export_json()

    def write_report(
        self,
        research_question: str,
        papers: List[Paper],
        filename: Optional[str] = None,
    ) -> Path:
        """Generate and save a full research report. Returns the file path."""
        report = self.report_writer.generate_report(research_question, papers)
        return self.report_writer.save_report(report, filename=filename)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)
        logger.info(msg)
