"""Small OpenAI-compatible client with a deterministic offline fallback."""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.config import EMBEDDING_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self) -> None:
        self._client = None
        self.last_error: str | None = None
        if OPENAI_API_KEY:
            try:
                from openai import OpenAI

                kwargs: dict[str, Any] = {"api_key": OPENAI_API_KEY}
                if OPENAI_BASE_URL:
                    kwargs["base_url"] = OPENAI_BASE_URL
                self._client = OpenAI(**kwargs)
            except Exception:
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        if not self._client:
            return None
        try:
            response = self._client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception:
            return None

    def complete_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Make exactly one structured-output request; failures are not retried."""
        if not self._client:
            self.last_error = "client_unavailable"
            return None
        try:
            request: dict[str, Any] = {
                "model": OPENAI_MODEL,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "neuroguard_analysis",
                        "strict": True,
                        "schema": json_schema,
                    },
                },
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
            if not OPENAI_MODEL.startswith("gpt-5"):
                request["temperature"] = 0
            response = self._client.chat.completions.create(**request)
            content = response.choices[0].message.content or "{}"
            self.last_error = None
            return json.loads(content)
        except Exception as error:
            # Provider exceptions can contain request fragments or sensitive
            # transport details. Keep diagnostics useful without echoing them.
            self.last_error = f"{type(error).__name__}: provider_request_failed"
            logger.warning("Unified LLM call failed: %s", self.last_error)
            return None

    def complete_text(self, system_prompt: str, user_prompt: str) -> str | None:
        if not self._client:
            return None
        try:
            response = self._client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content
        except Exception:
            return None

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        if not self._client:
            return None
        try:
            response = self._client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
            return [item.embedding for item in response.data]
        except Exception:
            return None
