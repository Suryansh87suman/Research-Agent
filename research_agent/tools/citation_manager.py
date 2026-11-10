"""
citation_manager.py — Manage, format, and export academic citations.

Supports export formats:
- BibTeX (.bib)
- APA 7th edition (plain text)
- MLA 9th edition (plain text)
- JSON
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from research_agent import config
from research_agent.tools.literature_search import Paper

logger = logging.getLogger(__name__)


class CitationManagerTool:
    """
    Stores papers in an in-memory library and exports references in multiple formats.

    Usage
    -----
    manager = CitationManagerTool()
    manager.add_papers(papers)
    manager.export_bibtex("refs.bib")
    """

    def __init__(self) -> None:
        self._library: Dict[str, Paper] = {}   # key → Paper

    # ── Library management ────────────────────────────────────────────────────

    def add_paper(self, paper: Paper) -> str:
        """
        Add a paper to the library.

        Returns
        -------
        str
            The citation key assigned to the paper.
        """
        key = self._make_key(paper)
        self._library[key] = paper
        logger.debug("Added citation: %s", key)
        return key

    def add_papers(self, papers: List[Paper]) -> List[str]:
        """Add multiple papers and return their citation keys."""
        return [self.add_paper(p) for p in papers]

    def get_paper(self, key: str) -> Optional[Paper]:
        return self._library.get(key)

    def list_keys(self) -> List[str]:
        return list(self._library.keys())

    def clear(self) -> None:
        self._library.clear()

    def __len__(self) -> int:
        return len(self._library)

    # ── Formatting ────────────────────────────────────────────────────────────

    def format_apa(self, paper: Paper) -> str:
        """Return an APA 7th edition citation string."""
        authors = self._apa_authors(paper.authors)
        year = paper.year or "n.d."
        title = paper.title
        venue = paper.venue or paper.source
        doi_part = f" https://doi.org/{paper.doi}" if paper.doi else (
            f" {paper.url}" if paper.url else ""
        )
        return f"{authors} ({year}). {title}. *{venue}*.{doi_part}"

    def format_mla(self, paper: Paper) -> str:
        """Return an MLA 9th edition citation string."""
        if not paper.authors:
            author_str = "Unknown Author"
        elif len(paper.authors) == 1:
            parts = paper.authors[0].rsplit(" ", 1)
            author_str = f"{parts[-1]}, {parts[0]}" if len(parts) == 2 else paper.authors[0]
        else:
            parts = paper.authors[0].rsplit(" ", 1)
            first_author = f"{parts[-1]}, {parts[0]}" if len(parts) == 2 else paper.authors[0]
            author_str = f"{first_author}, et al."
        year = paper.year or "n.d."
        venue = paper.venue or paper.source
        doi_part = f" doi:{paper.doi}." if paper.doi else ""
        return f'{author_str}. "{paper.title}." *{venue}*, {year}.{doi_part}'

    def format_bibtex_entry(self, key: str, paper: Paper) -> str:
        """Return a single BibTeX entry string."""
        entry_type = "article"
        fields: Dict[str, str] = {
            "title": self._bibtex_escape(paper.title),
            "author": " and ".join(paper.authors) if paper.authors else "Unknown",
            "year": str(paper.year) if paper.year else "",
            "journal": paper.venue or paper.source,
            "abstract": self._bibtex_escape((paper.abstract or "")[:500]),
            "url": paper.url,
        }
        if paper.doi:
            fields["doi"] = paper.doi

        lines = [f"@{entry_type}{{{key},"]
        for field_name, value in fields.items():
            if value:
                lines.append(f"  {field_name} = {{{value}}},")
        lines.append("}")
        return "\n".join(lines)

    # ── Export ────────────────────────────────────────────────────────────────

    def export_bibtex(self, filename: Optional[str] = None) -> Path:
        """
        Export all citations to a .bib file.

        Returns
        -------
        Path
            Path to the written .bib file.
        """
        filename = filename or "references.bib"
        out_path = config.OUTPUT_DIR / filename
        entries = [
            self.format_bibtex_entry(key, paper)
            for key, paper in self._library.items()
        ]
        out_path.write_text("\n\n".join(entries), encoding="utf-8")
        logger.info("Exported %d BibTeX entries to %s", len(entries), out_path)
        return out_path

    def export_apa(self, filename: Optional[str] = None) -> Path:
        """Export all citations as APA 7th references."""
        filename = filename or "references_apa.txt"
        out_path = config.OUTPUT_DIR / filename
        lines = sorted(
            (self.format_apa(p) for p in self._library.values()),
            key=lambda s: s.lower(),
        )
        out_path.write_text("\n\n".join(lines), encoding="utf-8")
        logger.info("Exported %d APA citations to %s", len(lines), out_path)
        return out_path

    def export_json(self, filename: Optional[str] = None) -> Path:
        """Export the full library as JSON."""
        filename = filename or "references.json"
        out_path = config.OUTPUT_DIR / filename
        data = {
            key: {
                "title": p.title,
                "authors": p.authors,
                "abstract": p.abstract,
                "year": p.year,
                "source": p.source,
                "url": p.url,
                "doi": p.doi,
                "venue": p.venue,
                "citation_count": p.citation_count,
                "keywords": p.keywords,
            }
            for key, p in self._library.items()
        }
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Exported citation library (%d items) to %s", len(data), out_path)
        return out_path

    def get_formatted_list(self, fmt: str = "apa") -> str:
        """
        Return all citations as a formatted string.

        Parameters
        ----------
        fmt : str
            'apa' | 'mla' | 'bibtex'
        """
        if fmt == "bibtex":
            return "\n\n".join(
                self.format_bibtex_entry(k, p) for k, p in self._library.items()
            )
        formatter = self.format_apa if fmt == "apa" else self.format_mla
        lines = [formatter(p) for p in self._library.values()]
        return "\n\n".join(sorted(lines, key=str.lower))

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _make_key(paper: Paper) -> str:
        """Generate a unique citation key: FirstAuthorLastNameYearShortTitle."""
        last_name = "Unknown"
        if paper.authors:
            parts = paper.authors[0].strip().rsplit(" ", 1)
            last_name = re.sub(r"[^a-zA-Z]", "", parts[-1]) or "Unknown"
        year = str(paper.year) if paper.year else "nd"
        title_words = re.sub(r"[^a-zA-Z0-9 ]", "", paper.title).split()
        short_title = "".join(w.capitalize() for w in title_words[:3])
        return f"{last_name}{year}{short_title}"

    @staticmethod
    def _apa_authors(authors: List[str]) -> str:
        """Format author list in APA style."""
        if not authors:
            return "Unknown Author"

        def fmt(name: str) -> str:
            parts = name.strip().rsplit(" ", 1)
            if len(parts) == 2:
                initials = ". ".join(p[0] for p in parts[0].split()) + "."
                return f"{parts[1]}, {initials}"
            return name

        if len(authors) == 1:
            return fmt(authors[0])
        if len(authors) <= 20:
            formatted = [fmt(a) for a in authors]
            return ", ".join(formatted[:-1]) + ", & " + formatted[-1]
        # APA 7th: first 19 + … + last
        formatted = [fmt(a) for a in authors[:19]]
        return ", ".join(formatted) + ", … " + fmt(authors[-1])

    @staticmethod
    def _bibtex_escape(text: str) -> str:
        """Escape special LaTeX/BibTeX characters."""
        replacements = {
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\^{}",
        }
        for char, escaped in replacements.items():
            text = text.replace(char, escaped)
        return text
