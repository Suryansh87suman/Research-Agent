# conftest.py — shared pytest configuration
import sys
import os

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set mock env vars so config.py doesn't raise during test collection
os.environ.setdefault("IBM_WATSONX_API_KEY", "test_api_key_placeholder")
os.environ.setdefault("IBM_WATSONX_PROJECT_ID", "test_project_id_placeholder")
os.environ.setdefault("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
os.environ.setdefault("GRANITE_MODEL_ID", "ibm/granite-3-8b-instruct")
os.environ.setdefault("OUTPUT_DIR", "outputs")
