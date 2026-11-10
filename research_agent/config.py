"""
config.py — Load and validate environment variables for the Research Agent.
All IBM Cloud / Granite settings are sourced from the .env file.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env (support both .env and .env.local) ────────────────────────────
_base = Path(__file__).resolve().parent.parent
for _candidate in (_base / ".env", _base / ".env.local"):
    if _candidate.exists():
        load_dotenv(_candidate)
        break


def _require(key: str) -> str:
    """Return env var or raise a clear error if it is missing / placeholder."""
    value = os.getenv(key, "").strip()
    if not value or value.startswith("your_"):
        raise EnvironmentError(
            f"Missing or unconfigured environment variable: {key}\n"
            f"Please edit .env.local (copy of env.example) and set a real value."
        )
    return value


# ── IBM watsonx.ai ────────────────────────────────────────────────────────────
IBM_WATSONX_API_KEY: str = _require("IBM_WATSONX_API_KEY")
IBM_WATSONX_PROJECT_ID: str = _require("IBM_WATSONX_PROJECT_ID")
IBM_WATSONX_URL: str = os.getenv(
    "IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com"
)
GRANITE_MODEL_ID: str = os.getenv(
    "GRANITE_MODEL_ID", "meta-llama/llama-3-3-70b-instruct"
)

# ── Granite generation parameters ────────────────────────────────────────────
GRANITE_MAX_TOKENS: int = int(os.getenv("GRANITE_MAX_TOKENS", "1024"))
GRANITE_TEMPERATURE: float = float(os.getenv("GRANITE_TEMPERATURE", "0.7"))
GRANITE_TOP_P: float = float(os.getenv("GRANITE_TOP_P", "0.95"))

# ── Research sources ──────────────────────────────────────────────────────────
SEMANTIC_SCHOLAR_API_KEY: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
CROSSREF_POLITE_EMAIL: str = os.getenv("CROSSREF_POLITE_EMAIL", "")
ARXIV_MAX_RESULTS: int = int(os.getenv("ARXIV_MAX_RESULTS", "10"))
MAX_PAPERS_PER_QUERY: int = int(os.getenv("MAX_PAPERS_PER_QUERY", "10"))

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
