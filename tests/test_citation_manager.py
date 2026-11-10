"""
tests/test_citation_manager.py — Unit tests for CitationManagerTool.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from research_agent.tools.literature_search import Paper
from research_agent.tools.citation_manager import CitationManagerTool


@pytest.fixture
def sample_papers():
    return [
        Paper(
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
            abstract="The dominant sequence transduction models are based on complex recurrent neural networks.",
            year=2017,
            source="arxiv",
            doi="10.48550/arXiv.1706.03762",
            venue="NeurIPS",
            url="https://arxiv.org/abs/1706.03762",
        ),
        Paper(
            title="BERT: Pre-training of Deep Bidirectional Transformers",
            authors=["Jacob Devlin", "Ming-Wei Chang"],
            abstract="We introduce a new language representation model called BERT.",
            year=2019,
            source="semantic_scholar",
            doi="10.18653/v1/N19-1423",
            venue="NAACL",
            url="https://aclanthology.org/N19-1423",
        ),
    ]


@pytest.fixture
def manager():
    return CitationManagerTool()


class TestCitationManagerTool:
    def test_add_paper_returns_key(self, manager, sample_papers):
        key = manager.add_paper(sample_papers[0])
        assert isinstance(key, str)
        assert len(key) > 0

    def test_add_papers_returns_all_keys(self, manager, sample_papers):
        keys = manager.add_papers(sample_papers)
        assert len(keys) == 2

    def test_library_length(self, manager, sample_papers):
        manager.add_papers(sample_papers)
        assert len(manager) == 2

    def test_apa_format_contains_year(self, manager, sample_papers):
        formatted = manager.format_apa(sample_papers[0])
        assert "2017" in formatted
        assert "Vaswani" in formatted

    def test_mla_format(self, manager, sample_papers):
        formatted = manager.format_mla(sample_papers[0])
        assert "Vaswani" in formatted
        assert "Attention" in formatted

    def test_bibtex_entry_structure(self, manager, sample_papers):
        entry = manager.format_bibtex_entry("Vaswani2017Attention", sample_papers[0])
        assert "@article{Vaswani2017Attention," in entry
        assert "title" in entry
        assert "author" in entry

    def test_get_formatted_list_apa(self, manager, sample_papers):
        manager.add_papers(sample_papers)
        result = manager.get_formatted_list(fmt="apa")
        assert "Vaswani" in result or "Devlin" in result

    def test_clear_empties_library(self, manager, sample_papers):
        manager.add_papers(sample_papers)
        manager.clear()
        assert len(manager) == 0

    def test_make_key_format(self):
        paper = Paper(
            title="Deep Neural Networks Are Robust",
            authors=["Jane Smith"],
            abstract="",
            year=2022,
            source="arxiv",
        )
        key = CitationManagerTool._make_key(paper)
        assert "Smith" in key
        assert "2022" in key

    @patch("research_agent.tools.citation_manager.config")
    def test_export_json(self, mock_config, tmp_path, manager, sample_papers):
        mock_config.OUTPUT_DIR = tmp_path
        manager.add_papers(sample_papers)
        out = manager.export_json("test_refs.json")
        assert out.exists()
        data = json.loads(out.read_text())
        assert len(data) == 2
