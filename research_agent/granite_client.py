"""
granite_client.py — Thin wrapper around ibm-watsonx-ai for IBM Granite models.
Handles authentication (IAM), text generation, and prompt helpers.
"""

import logging
import time
from typing import Optional
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

from research_agent import config

logger = logging.getLogger(__name__)


class GraniteClient:
    """
    Wraps IBM watsonx.ai ModelInference for IBM Granite.

    Usage
    -----
    client = GraniteClient()
    response = client.generate("Summarise this paper: ...")
    """

    def __init__(self) -> None:
        credentials = Credentials(
            url=config.IBM_WATSONX_URL,
            api_key=config.IBM_WATSONX_API_KEY,
        )
        self._model = ModelInference(
            model_id=config.GRANITE_MODEL_ID,
            credentials=credentials,
            project_id=config.IBM_WATSONX_PROJECT_ID,
            params={
                GenParams.MAX_NEW_TOKENS: config.GRANITE_MAX_TOKENS,
                GenParams.TEMPERATURE: config.GRANITE_TEMPERATURE,
                GenParams.TOP_P: config.GRANITE_TOP_P,
                GenParams.STOP_SEQUENCES: ["<|eot_id|>", "<|end_of_text|>"],
            },
        )
        logger.info(
            "GraniteClient initialised — model: %s | project: %s",
            config.GRANITE_MODEL_ID,
            config.IBM_WATSONX_PROJECT_ID,
        )

    # ── Public helpers ────────────────────────────────────────────────────────

    # Retry settings for IBM Cloud Lite rate-limiting (HTTP 429)
    _MAX_RETRIES = 6
    _RETRY_BASE  = 5   # seconds — doubles each attempt: 5, 10, 20, 40, 80, 160

    def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """
        Send a prompt to IBM Granite and return the generated text.
        Automatically retries on HTTP 429 (rate limit) with exponential backoff.

        Parameters
        ----------
        prompt : str
            The full prompt string.
        max_tokens : int, optional
            Override the default max-token setting for this call.

        Returns
        -------
        str
            The model's generated text, stripped of leading/trailing whitespace.
        """
        params: dict = {}
        if max_tokens is not None:
            params[GenParams.MAX_NEW_TOKENS] = max_tokens

        last_exc: Exception = RuntimeError("No attempts made.")
        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                logger.debug(
                    "Sending prompt (%d chars) to Granite (attempt %d) …",
                    len(prompt), attempt,
                )
                result = self._model.generate_text(
                    prompt=prompt, params=params or None
                )
                logger.debug("Received response (%d chars).", len(result))
                return result.strip()

            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                err_str = str(exc)
                if "429" in err_str or "consumption_limit_reached" in err_str:
                    wait = self._RETRY_BASE * (2 ** (attempt - 1))
                    logger.warning(
                        "IBM API rate limit hit (attempt %d/%d). "
                        "Waiting %ds before retry…",
                        attempt, self._MAX_RETRIES, wait,
                    )
                    time.sleep(wait)
                else:
                    raise  # non-429 errors surface immediately

        raise last_exc

    def generate_with_system(
        self, system_prompt: str, user_message: str, max_tokens: Optional[int] = None
    ) -> str:
        """
        Combine a system instruction with a user message using the
        Llama-3 instruct chat-token format, compatible with
        meta-llama/llama-3-3-70b-instruct and similar instruct models
        available on IBM Cloud Lite.
        """
        full_prompt = (
            f"<|begin_of_text|>"
            f"<|start_header_id|>system<|end_header_id|>\n\n"
            f"{system_prompt.strip()}<|eot_id|>"
            f"<|start_header_id|>user<|end_header_id|>\n\n"
            f"{user_message.strip()}<|eot_id|>"
            f"<|start_header_id|>assistant<|end_header_id|>\n\n"
        )
        return self.generate(full_prompt, max_tokens=max_tokens)
