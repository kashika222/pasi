"""LLM provider clients for PASI document analysis.

Supported providers:
- ``openai`` — OpenAI Chat Completions (paid / trial credits)
- ``gemini`` — Google AI Studio free tier (recommended for students)
"""

from __future__ import annotations

import json
from typing import Any, Protocol

import requests

from pasi.config.settings import Settings, get_settings
from pasi.logging.setup import get_logger

logger = get_logger(__name__)


class LLMClientError(RuntimeError):
    """Raised when an LLM provider call fails."""


class LLMClient(Protocol):
    model_id: str

    def chat_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        model: str | None = None,
    ) -> dict[str, Any]: ...


class OpenAIClient:
    """OpenAI Chat Completions wrapper."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        api_key = self.settings.openai_api_key or self.settings.llm_api_key
        if not api_key:
            raise LLMClientError(
                "OpenAI API key missing. Set PASI_OPENAI_API_KEY or PASI_LLM_API_KEY"
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMClientError("Install openai: uv add openai") from exc

        self._client = OpenAI(api_key=api_key)
        self.model_id = self.settings.openai_model

    def chat_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        model_id = model or self.model_id
        temperature = (
            self.settings.openai_temperature if temperature is None else temperature
        )
        logger.info("OpenAI chat.completions create model=%s", model_id)
        try:
            response = self._client.chat.completions.create(
                model=model_id,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("OpenAI API request failed")
            raise LLMClientError(str(exc)) from exc

        content = response.choices[0].message.content or ""
        return _parse_json_object(content)


class GeminiClient:
    """Google Gemini generateContent wrapper (AI Studio free tier)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        api_key = self.settings.gemini_api_key or self.settings.llm_api_key
        if not api_key:
            raise LLMClientError(
                "Gemini API key missing. Set PASI_GEMINI_API_KEY "
                "(get a free key at https://aistudio.google.com/apikey)"
            )
        if api_key.startswith("sk-"):
            raise LLMClientError(
                "PASI_LLM_API_KEY looks like an OpenAI key, but provider=gemini. "
                "Set PASI_GEMINI_API_KEY to your Google AI Studio key instead."
            )
        self._api_key = api_key
        self.model_id = self.settings.gemini_model

    def chat_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        model_id = model or self.model_id
        temperature = (
            self.settings.openai_temperature if temperature is None else temperature
        )
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_id}:generateContent"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
        logger.info("Gemini generateContent model=%s", model_id)
        try:
            response = requests.post(
                url,
                params={"key": self._api_key},
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            logger.exception("Gemini API request failed")
            detail = ""
            if getattr(exc, "response", None) is not None and exc.response is not None:
                detail = f" | {exc.response.text[:500]}"
            # Never echo API keys that may appear in request URLs.
            message = str(exc)
            if "key=" in message:
                message = message.split("key=")[0] + "key=REDACTED"
            raise LLMClientError(f"{message}{detail}") from exc

        try:
            content = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMClientError(f"Unexpected Gemini response shape: {body}") from exc
        return _parse_json_object(content)


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    """Factory: choose provider from ``PASI_LLM_PROVIDER`` (openai|gemini)."""
    settings = settings or get_settings()
    provider = (settings.llm_provider or "openai").strip().lower()
    if provider == "gemini":
        return GeminiClient(settings=settings)
    if provider == "openai":
        return OpenAIClient(settings=settings)
    raise LLMClientError(
        f"Unsupported PASI_LLM_PROVIDER={provider!r}. Use 'openai' or 'gemini'."
    )


def _parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMClientError(f"Model returned invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise LLMClientError("Model JSON root must be an object")
    return payload
