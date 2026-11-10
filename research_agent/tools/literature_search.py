"""
literature_search.py — Search academic literature from multiple sources.

Sources
-------
- arXiv (via `arxiv` library)
- Semantic Scholar (REST API)
- CrossRef (REST API)
"""

import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional
import arxiv
import requests

from research_agent import config

logger = logging.getLogger(__name__)


@dataclass
class Paper:
    """Represents a single research paper."""

    title: str
    authors: List[str]
    abstract: str
    year: Optional[int]
    source: str                        # 'arxiv' | 'semantic_scholar' | 'crossref'
    url: str = ""
    doi: str = ""
    venue: str = ""
    citation_count: int = 0
    keywords: List[str] = field(default_factory=list)

    def short_ref(self) -> str:
        """Return a compact one-line reference string."""
        author_str = self.authors[0] if self.authors else "Unknown"
        if len(self.authors) > 1:
            author_str += " et al."
        return f"{author_str} ({self.year or '?'}). {self.title}. {self.venue or self.source}."


class LiteratureSearchTool:
    """
    Searches academic databases for papers matching a research query.

    Parameters
    ----------
    max_results : int
        Maximum papers to return per source (default from config).
    """

    _SS_BASE = "https://api.semanticscholar.org/graph/v1"
    _CR_BASE = "https://api.crossref.org/works"

    def __init__(self, max_results: Optional[int] = None) -> None:
        self.max_results = max_results or config.MAX_PAPERS_PER_QUERY

    # ── Public API ────────────────────────────────────────────────────────────

    def search(self, query: str, sources: Optional[List[str]] = None) -> List[Paper]:
        """
        Search for papers matching *query* across the requested sources.

        Parameters
        ----------
        query : str
            Natural-language or keyword research question.
        sources : list of str, optional
            Subset of ['arxiv', 'semantic_scholar', 'crossref'].
            Defaults to all three.

        Returns
        -------
        list of Paper
            Deduplicated list sorted by (year desc, citation_count desc).
        """
        sources = sources or ["arxiv", "semantic_scholar", "crossref"]
        results: List[Paper] = []

        if "arxiv" in sources:
            results.extend(self._search_arxiv(query))
        if "semantic_scholar" in sources:
            results.extend(self._search_semantic_scholar(query))
        if "crossref" in sources:
            results.extend(self._search_crossref(query))

        deduplicated = self._deduplicate(results)
        deduplicated.sort(
            key=lambda p: (p.year or 0, p.citation_count), reverse=True
        )
        logger.info(
            "Literature search for '%s': %d papers found.", query, len(deduplicated)
        )
        return deduplicated[: self.max_results]

    # ── arXiv ─────────────────────────────────────────────────────────────────

    def _search_arxiv(self, query: str) -> List[Paper]:
        papers: List[Paper] = []
        try:
            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=self.max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )
            for result in client.results(search):
                papers.append(
                    Paper(
                        title=result.title,
                        authors=[str(a) for a in result.authors],
                        abstract=result.summary,
                        year=result.published.year if result.published else None,
                        source="arxiv",
                        url=result.entry_id,
                        doi=result.doi or "",
                        venue="arXiv",
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("arXiv search failed: %s", exc)
        return papers

    # ── Semantic Scholar ──────────────────────────────────────────────────────

    def _search_semantic_scholar(self, query: str) -> List[Paper]:
        papers: List[Paper] = []
        headers: dict = {}
        if config.SEMANTIC_SCHOLAR_API_KEY:
            headers["x-api-key"] = config.SEMANTIC_SCHOLAR_API_KEY
        try:
            resp = requests.get(
                f"{self._SS_BASE}/paper/search",
                params={
                    "query": query,
                    "limit": self.max_results,
                    "fields": "title,authors,abstract,year,externalIds,venue,citationCount",
                },
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            for item in resp.json().get("data", []):
                papers.append(
                    Paper(
                        title=item.get("title", ""),
                        authors=[a.get("name", "") for a in item.get("authors", [])],
                        abstract=item.get("abstract") or "",
                        year=item.get("year"),
                        source="semantic_scholar",
                        url=f"https://www.semanticscholar.org/paper/{item.get('paperId', '')}",
                        doi=item.get("externalIds", {}).get("DOI", ""),
                        venue=item.get("venue", ""),
                        citation_count=item.get("citationCount", 0),
                    )
                )
            time.sleep(0.5)  # polite rate limiting
        except Exception as exc:  # noqa: BLE001
            logger.warning("Semantic Scholar search failed: %s", exc)
        return papers

    # ── CrossRef ──────────────────────────────────────────────────────────────

    def _search_crossref(self, query: str) -> List[Paper]:
        papers: List[Paper] = []
        params: dict = {
            "query": query,
            "rows": self.max_results,
            "select": "title,author,abstract,published,DOI,container-title",
        }
        if config.CROSSREF_POLITE_EMAIL:
            params["mailto"] = config.CROSSREF_POLITE_EMAIL
        try:
            resp = requests.get(self._CR_BASE, params=params, timeout=15)
            resp.raise_for_status()
            for item in resp.json().get("message", {}).get("items", []):
                title_list = item.get("title", [])
                title = title_list[0] if title_list else ""
                raw_authors = item.get("author", [])
                authors = [
                    f"{a.get('given', '')} {a.get('family', '')}".strip()
                    for a in raw_authors
                ]
                year_parts = item.get("published", {}).get("date-parts", [[None]])
                year = year_parts[0][0] if year_parts and year_parts[0] else None
                venue_list = item.get("container-title", [])
                venue = venue_list[0] if venue_list else ""
                papers.append(
                    Paper(
                        title=title,
                        authors=authors,
                        abstract=item.get("abstract", ""),
                        year=year,
                        source="crossref",
                        url=f"https://doi.org/{item.get('DOI', '')}",
                        doi=item.get("DOI", ""),
                        venue=venue,
                    )
                )
            time.sleep(0.5)
        except Exception as exc:  # noqa: BLE001
            logger.warning("CrossRef search failed: %s", exc)
        return papers

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _deduplicate(papers: List[Paper]) -> List[Paper]:
        """Deduplicate by DOI (if available) then by normalised title."""
        seen_doi: set = set()
        seen_title: set = set()
        unique: List[Paper] = []
        for paper in papers:
            if paper.doi:
                if paper.doi.lower() in seen_doi:
                    continue
                seen_doi.add(paper.doi.lower())
            norm_title = paper.title.lower().strip()
            if norm_title in seen_title:
                continue
            seen_title.add(norm_title)
            unique.append(paper)
        return unique
