"""
tests/test_literature_search.py — Unit tests for LiteratureSearchTool.
Uses mocked HTTP calls; no live network access required.
"""

import pytest
from unittest.mock import patch, MagicMock
from research_agent.tools.literature_search import LiteratureSearchTool, Paper


class TestPaper:
    def test_short_ref_single_author(self):
        paper = Paper(
            title="Deep Learning for Science",
            authors=["Alice Smith"],
            abstract="A study on deep learning.",
            year=2023,
            source="arxiv",
        )
        ref = paper.short_ref()
        assert "Smith" in ref or "Alice" in ref
        assert "2023" in ref

    def test_short_ref_multi_author(self):
        paper = Paper(
            title="Quantum Computing Survey",
            authors=["Bob Jones", "Carol White", "Dave Brown"],
            abstract="Survey of quantum computing.",
            year=2022,
            source="semantic_scholar",
        )
        ref = paper.short_ref()
        assert "et al." in ref
        assert "2022" in ref


class TestLiteratureSearchTool:
    def test_deduplicate_by_doi(self):
        papers = [
            Paper(title="Paper A", authors=["X"], abstract="", year=2020, source="arxiv", doi="10.1234/test"),
            Paper(title="Paper A duplicate", authors=["Y"], abstract="", year=2020, source="crossref", doi="10.1234/test"),
            Paper(title="Paper B", authors=["Z"], abstract="", year=2021, source="arxiv", doi="10.9999/other"),
        ]
        unique = LiteratureSearchTool._deduplicate(papers)
        assert len(unique) == 2

    def test_deduplicate_by_title(self):
        papers = [
            Paper(title="Identical Title", authors=["A"], abstract="", year=2020, source="arxiv"),
            Paper(title="identical title", authors=["B"], abstract="", year=2020, source="crossref"),
        ]
        unique = LiteratureSearchTool._deduplicate(papers)
        assert len(unique) == 1

    @patch("research_agent.tools.literature_search.arxiv")
    def test_search_arxiv_error_returns_empty(self, mock_arxiv):
        mock_arxiv.Client.side_effect = Exception("Network error")
        tool = LiteratureSearchTool(max_results=5)
        results = tool._search_arxiv("test query")
        assert results == []

    @patch("research_agent.tools.literature_search.requests.get")
    def test_search_semantic_scholar_parses_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "paperId": "abc123",
                    "title": "Test Paper",
                    "authors": [{"name": "John Doe"}],
                    "abstract": "Test abstract.",
                    "year": 2023,
                    "venue": "NeurIPS",
                    "citationCount": 42,
                    "externalIds": {"DOI": "10.0001/test"},
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        tool = LiteratureSearchTool(max_results=5)
        results = tool._search_semantic_scholar("deep learning")

        assert len(results) == 1
        assert results[0].title == "Test Paper"
        assert results[0].citation_count == 42
        assert results[0].doi == "10.0001/test"

    @patch("research_agent.tools.literature_search.requests.get")
    def test_search_crossref_parses_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "items": [
                    {
                        "title": ["CrossRef Paper"],
                        "author": [{"given": "Jane", "family": "Doe"}],
                        "abstract": "CrossRef abstract.",
                        "published": {"date-parts": [[2021]]},
                        "DOI": "10.0002/crossref",
                        "container-title": ["Nature"],
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        tool = LiteratureSearchTool(max_results=5)
        results = tool._search_crossref("machine learning")

        assert len(results) == 1
        assert results[0].title == "CrossRef Paper"
        assert results[0].year == 2021
        assert results[0].doi == "10.0002/crossref"
