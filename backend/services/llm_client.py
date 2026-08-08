"""Small OpenAI-compatible client with a deterministic offline fallback."""

from __future__ import annotations

import json
from typing import Any

from backend.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


class LLMClient:
    def __init__(self) -> None:
        self._client = None
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
