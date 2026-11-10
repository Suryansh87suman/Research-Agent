"""
tests/test_hypothesis_engine.py — Unit tests for HypothesisEngineTool.
IBM Granite calls are fully mocked.
"""

import pytest
from unittest.mock import MagicMock

from research_agent.tools.literature_search import Paper
from research_agent.tools.hypothesis_engine import HypothesisEngineTool


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.generate_with_system.return_value = (
        "H1. Transformer architectures improve drug binding prediction accuracy.\n"
        "H2. Pre-trained models reduce training data requirements by 50%.\n"
        "H3. Multi-modal fusion of protein structure and sequence yields superior results."
    )
    return client


@pytest.fixture
def sample_papers():
    return [
        Paper(
            title="AlphaFold: Protein structure prediction",
            authors=["John Jumper"],
            abstract="AlphaFold predicts protein structures with high accuracy using deep learning.",
            year=2021,
            source="arxiv",
        ),
        Paper(
            title="Drug discovery using transformers",
            authors=["Alice Chen", "Bob Lee"],
            abstract="Transformer models applied to molecular property prediction outperform previous methods.",
            year=2022,
            source="semantic_scholar",
        ),
    ]


class TestHypothesisEngineTool:
    def test_generate_hypotheses_returns_list(self, mock_client, sample_papers):
        engine = HypothesisEngineTool(mock_client)
        hypotheses = engine.generate_hypotheses(
            "transformers in drug discovery", sample_papers, count=3
        )
        assert isinstance(hypotheses, list)
        assert len(hypotheses) >= 1

    def test_generate_hypotheses_calls_granite(self, mock_client, sample_papers):
        engine = HypothesisEngineTool(mock_client)
        engine.generate_hypotheses("test question", sample_papers, count=2)
        mock_client.generate_with_system.assert_called_once()

    def test_refine_hypothesis(self, mock_client):
        mock_client.generate_with_system.return_value = "Refined: Transformers achieve 30% improvement."
        engine = HypothesisEngineTool(mock_client)
        refined = engine.refine_hypothesis(
            "Transformers improve accuracy.",
            "Be more specific about the metric and domain."
        )
        assert "Refined" in refined or len(refined) > 0

    def test_suggest_experiments(self, mock_client):
        mock_client.generate_with_system.return_value = (
            "1. Randomised controlled trial with protein binding assay.\n"
            "2. Benchmark on ChEMBL dataset."
        )
        engine = HypothesisEngineTool(mock_client)
        result = engine.suggest_experiments("Transformers improve drug binding prediction.")
        assert len(result) > 0

    def test_evaluate_hypothesis(self, mock_client, sample_papers):
        mock_client.generate_with_system.return_value = "Score: 8/10. Novel and feasible."
        engine = HypothesisEngineTool(mock_client)
        evaluation = engine.evaluate_hypothesis(
            "Pre-trained models generalise better.", sample_papers
        )
        assert "8" in evaluation or len(evaluation) > 0

    def test_parse_numbered_list_h_prefix(self):
        text = "H1. First item.\nH2. Second item.\nH3. Third item."
        items = HypothesisEngineTool._parse_numbered_list(text, 3)
        assert len(items) == 3
        assert all("item" in item for item in items)

    def test_parse_numbered_list_dot_prefix(self):
        text = "1. Alpha\n2. Beta\n3. Gamma"
        items = HypothesisEngineTool._parse_numbered_list(text, 3)
        assert len(items) == 3

    def test_count_clamp(self, mock_client, sample_papers):
        """count should be clamped to max 5."""
        engine = HypothesisEngineTool(mock_client)
        engine.generate_hypotheses("test", sample_papers, count=10)
        call_args = mock_client.generate_with_system.call_args[0][1]
        assert "5" in call_args
