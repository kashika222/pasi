"""Backward-compatible OpenAI client export."""

from pasi.ai.providers import LLMClientError as OpenAIClientError
from pasi.ai.providers import OpenAIClient

__all__ = ["OpenAIClient", "OpenAIClientError"]
