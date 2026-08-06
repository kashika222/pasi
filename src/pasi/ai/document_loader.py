"""Helpers to load clean document text for AI analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pasi.logging.setup import get_logger

logger = get_logger(__name__)


class DocumentLoadError(RuntimeError):
    """Raised when clean document text cannot be loaded."""


def load_clean_text(path: str | Path) -> tuple[str, dict[str, Any]]:
    """Load clean text from ``.txt`` / ``.md`` or a PASI collection JSON file.

    Returns
    -------
    text, metadata
        Extracted plain text and light provenance metadata when available.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise DocumentLoadError(f"Document not found: {file_path}")

    suffix = file_path.suffix.lower()
    metadata: dict[str, Any] = {
        "document_path": str(file_path),
        "suffix": suffix,
    }

    if suffix in {".txt", ".md", ".html", ".htm"}:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        metadata["loader"] = "plain_text"
        return text, metadata

    if suffix == ".json":
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise DocumentLoadError("JSON document must be an object")
        text = _extract_text_from_json(payload)
        metadata["loader"] = "pasi_json"
        metadata["company_id"] = payload.get("company_id")
        metadata["company_name"] = payload.get("company_name")
        metadata["source_type"] = (
            payload.get("source_type")
            if isinstance(payload.get("source_type"), str)
            else None
        )
        return text, metadata

    raise DocumentLoadError(
        f"Unsupported document type '{suffix}'. Use .txt/.md/.html or PASI .json"
    )


def _extract_text_from_json(payload: dict[str, Any]) -> str:
    content = payload.get("content")
    if isinstance(content, dict):
        if isinstance(content.get("text"), str) and content["text"].strip():
            return content["text"]
        # Employee-review aggregates: concatenate review_text fields.
        records = content.get("records")
        if isinstance(records, list):
            parts = [
                str(row.get("review_text", "")).strip()
                for row in records
                if isinstance(row, dict) and row.get("review_text")
            ]
            if parts:
                return "\n\n".join(parts)
    if isinstance(payload.get("text"), str) and payload["text"].strip():
        return payload["text"]
    raise DocumentLoadError(
        "JSON does not contain content.text, content.records[].review_text, or text"
    )


def prepare_text(text: str, *, max_chars: int) -> tuple[str, dict[str, Any]]:
    """Trim whitespace and optionally truncate long documents for the model context."""
    cleaned = text.strip()
    meta: dict[str, Any] = {
        "original_char_count": len(cleaned),
        "truncated": False,
        "max_chars": max_chars,
    }
    if max_chars > 0 and len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars]
        meta["truncated"] = True
        logger.warning(
            "Document truncated from %s to %s characters for AI analysis",
            meta["original_char_count"],
            max_chars,
        )
    meta["sent_char_count"] = len(cleaned)
    return cleaned, meta
