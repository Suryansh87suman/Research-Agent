# IBM Research Agent

> **An autonomous AI research assistant powered by IBM Granite on IBM Cloud Lite.**  
> Searches academic literature, summarises papers, generates hypotheses, manages citations, and writes full research reports — all through a single CLI command.

---

## Table of Contents

- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration (.env)](#configuration-env)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [IBM Cloud Lite Setup Guide](#ibm-cloud-lite-setup-guide)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Research Agent CLI                    │
│                       (main.py)                         │
└────────────────────────┬────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │   ResearchAgent     │  ← Orchestrator
              │    (agent.py)       │
              └──┬──┬──┬──┬──┬─────┘
                 │  │  │  │  │
    ┌────────────┘  │  │  │  └─────────────────────┐
    │               │  │  │                         │
    ▼               ▼  │  ▼                         ▼
Literature     Summarizer│  Citation           Hypothesis
Search Tool   (IBM Granite)  Manager             Engine
(arxiv /       │        │  (BibTeX/APA/JSON)  (IBM Granite)
 Semantic      │        ▼
 Scholar /     │    Report Writer
 CrossRef)     │    (IBM Granite)
               │
               ▼
        ┌─────────────────┐
        │  GraniteClient  │  ← IBM watsonx.ai SDK
        │  ibm/granite-   │
        │  3-8b-instruct  │
        └─────────────────┘
```

---

## Features

| Feature | Description |
|---|---|
| **Literature Search** | Queries arXiv, Semantic Scholar, and CrossRef simultaneously |
| **Paper Summarisation** | Abstract + full-text summaries using IBM Granite |
| **Key Findings Extraction** | Bulleted findings extracted by Granite |
| **Comparative Analysis** | Side-by-side comparison of multiple papers |
| **Hypothesis Generation** | Novel, testable hypotheses grounded in the literature |
| **Hypothesis Evaluation** | Plausibility scoring (1–10) via Granite |
| **Experiment Suggestion** | Concrete experimental designs per hypothesis |
| **Research Report** | Full 7-section Markdown report (auto-generated) |
| **Citation Management** | Export references as **BibTeX**, **APA 7th**, or **JSON** |
| **Rich CLI** | Progress bars, tables, and panels via `rich` |

---

## Prerequisites

- Python 3.9 or higher
- An **IBM Cloud Lite** account → [cloud.ibm.com](https://cloud.ibm.com)
- A **watsonx.ai** project (free on Lite tier)

---

## Quick Start

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd "IBM INTERNSHIP PROJECT"
pip install -r requirements.txt
```

### 2. Configure IBM Cloud credentials

```bash
# Copy the example env file
cp env.example .env.local

# Edit .env.local and fill in your credentials:
#   IBM_WATSONX_API_KEY   — your IBM Cloud API key
#   IBM_WATSONX_PROJECT_ID — your watsonx.ai project ID
#   IBM_WATSONX_URL       — regional endpoint (default: us-south)
```

### 3. Run the agent

```bash
python main.py --query "transformer models in drug discovery"
```

---

## Configuration (.env)

Copy `env.example` to `.env.local` and fill in the values below.

| Variable | Required | Description |
|---|---|---|
| `IBM_WATSONX_API_KEY` | ✅ | IBM Cloud API key (IAM) |
| `IBM_WATSONX_PROJECT_ID` | ✅ | watsonx.ai project ID |
| `IBM_WATSONX_URL` | — | Regional endpoint (default: `us-south`) |
| `GRANITE_MODEL_ID` | — | Granite model (default: `ibm/granite-3-1-8b-base`) |
| `GRANITE_MAX_TOKENS` | — | Max tokens per generation (default: `1024`) |
| `GRANITE_TEMPERATURE` | — | Temperature 0–1 (default: `0.7`) |
| `SEMANTIC_SCHOLAR_API_KEY` | — | Optional; increases API rate limits |
| `CROSSREF_POLITE_EMAIL` | — | Recommended; gets you into the polite pool |
| `MAX_PAPERS_PER_QUERY` | — | Papers per source per query (default: `10`) |
| `OUTPUT_DIR` | — | Output directory (default: `outputs/`) |

### Available Models on IBM Cloud Lite (Nov 2026)

```
ibm/granite-3-1-8b-base                          ← default (fast, efficient)
ibm/granite-4-h-small
ibm/granite-embedding-278m-multilingual
meta-llama/llama-3-3-70b-instruct                (instruct, chat-token format)
meta-llama/llama-3-1-8b
mistralai/mistral-small-3-1-24b-instruct-2503
```

---

## Usage

### Full pipeline (recommended)

```bash
python main.py --query "CRISPR applications in cancer therapy"
```

### Specify sources

```bash
python main.py --query "quantum computing" --sources arxiv --sources semantic_scholar
```

### Generate more hypotheses

```bash
python main.py --query "climate change and AI" --hypotheses 5
```

### Increase paper limit

```bash
python main.py --query "large language models" --max-papers 20
```

### Add comparative analysis

```bash
python main.py --query "federated learning privacy" --compare
```

### Skip report generation (faster)

```bash
python main.py --query "neural architecture search" --no-report
```

### Python API

```python
from research_agent import ResearchAgent

agent = ResearchAgent()

# Full pipeline
results = agent.run_pipeline("transformers in drug discovery")
print(results["report_path"])

# Individual tools
papers = agent.search("protein folding deep learning")
summary = agent.summarize_paper(papers[0])
hypotheses = agent.generate_hypotheses("protein folding", papers, count=3)
agent.add_citations(papers)
agent.export_citations("bibtex")
```

---

## Project Structure

```
IBM INTERNSHIP PROJECT/
├── main.py                          # CLI entry point
├── requirements.txt                 # Python dependencies
├── env.example                      # Environment variable template
├── .env.local                       # Your credentials (not in git)
│
├── research_agent/
│   ├── __init__.py
│   ├── agent.py                     # ResearchAgent orchestrator
│   ├── config.py                    # Env var loader & validation
│   ├── granite_client.py            # IBM watsonx.ai / Granite wrapper
│   │
│   └── tools/
│       ├── __init__.py
│       ├── literature_search.py     # arXiv + Semantic Scholar + CrossRef
│       ├── summarizer.py            # Paper summarisation (Granite)
│       ├── citation_manager.py      # BibTeX / APA / JSON export
│       ├── report_writer.py         # Full report generation (Granite)
│       └── hypothesis_engine.py     # Hypothesis gen + evaluation (Granite)
│
├── outputs/                         # Generated reports & citations
│
└── tests/
    ├── conftest.py
    ├── test_literature_search.py
    ├── test_citation_manager.py
    └── test_hypothesis_engine.py
```

---

## Running Tests

Tests use mocked IBM Granite calls — no live credentials needed.

```bash
pip install pytest
pytest tests/ -v
```

Expected output:
```
tests/test_citation_manager.py ............  PASSED
tests/test_hypothesis_engine.py .........   PASSED
tests/test_literature_search.py .........   PASSED
```

---

## IBM Cloud Lite Setup Guide

1. **Create an IBM Cloud account** at [cloud.ibm.com](https://cloud.ibm.com) (free, no credit card)

2. **Create a watsonx.ai instance**
   - Go to **Catalog → AI / Machine Learning → watsonx.ai**
   - Select **Lite plan** → Create

3. **Create a Project**
   - In [dataplatform.ibm.com](https://dataplatform.ibm.com), click **New project → Empty project**
   - Note the **Project ID** from the project settings

4. **Generate an API Key**
   - Go to **Manage → Access (IAM) → API keys** → Create
   - Copy the key immediately (shown only once)

5. **Update `.env.local`**
   ```
   IBM_WATSONX_API_KEY=<your-api-key>
   IBM_WATSONX_PROJECT_ID=<your-project-id>
   ```

6. **Run the agent!**
   ```bash
   python main.py --query "your research question here"
   ```

---

## Technology Stack

| Component | Technology |
|---|---|
| **LLM** | IBM Granite (`ibm/granite-3-1-8b-base`) |
| **Platform** | IBM watsonx.ai on IBM Cloud Lite |
| **SDK** | `ibm-watsonx-ai` |
| **Literature** | arXiv API, Semantic Scholar API, CrossRef API |
| **CLI** | `click` + `rich` |
| **Citations** | Custom BibTeX / APA / MLA / JSON formatter |
| **Tests** | `pytest` with mocked Granite calls |

---

*Powered by IBM Granite on IBM Cloud Lite — Problem Statement #1: Research Agent*
