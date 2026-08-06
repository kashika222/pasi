"""AI-assisted document analysis → structured JSON with confidence scores."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pasi.ai.document_loader import DocumentLoadError, load_clean_text
from pasi.ai.prompts import PromptLoadError, load_and_render
from pasi.ai.providers import LLMClient, LLMClientError, get_llm_client
from pasi.ai.schema import (
    ANALYSIS_SCHEMA_VERSION,
    DIMENSION_LABELS,
    DimensionAssessment,
    DocumentAnalysisResult,
    empty_dimensions,
)
from pasi.clean.text import prepare_filing_text
from pasi.config.settings import Settings, get_settings
from pasi.logging.setup import get_logger

logger = get_logger(__name__)

PROMPT_VERSION = "document_analysis_v1"
SYSTEM_PROMPT_FILE = "document_analysis_system_v1.txt"
USER_PROMPT_FILE = "document_analysis_user_v1.txt"


class AnalysisError(RuntimeError):
    """Raised for unexpected analysis failures outside envelope handling."""


def analyze_text(
    text: str,
    *,
    company_id: str | None = None,
    company_name: str | None = None,
    source_type: str | None = None,
    document_path: str | None = None,
    settings: Settings | None = None,
    client: LLMClient | None = None,
    save: bool = True,
) -> DocumentAnalysisResult:
    """Analyze clean document text and return structured JSON-ready results."""
    settings = settings or get_settings()
    default_model = (
        settings.gemini_model
        if (settings.llm_provider or "").lower() == "gemini"
        else settings.openai_model
    )
    prepared, prep_meta = prepare_filing_text(
        text, max_chars=settings.openai_max_input_chars
    )

    if not prepared:
        result = DocumentAnalysisResult(
            company_id=company_id,
            company_name=company_name,
            source_type=source_type,
            document_path=document_path,
            model_id=default_model,
            prompt_version=PROMPT_VERSION,
            status="error",
            dimensions=empty_dimensions(),
            overall_confidence=0.0,
            metadata={"preparation": prep_meta},
            errors=["Input text is empty"],
        )
        if save:
            _persist(result, settings=settings)
        return result

    try:
        system_prompt = load_and_render(
            SYSTEM_PROMPT_FILE,
            {
                "DIMENSION_LIST": _dimension_list_for_prompt(),
                "SCORE_RUBRIC": (
                    "0 = not present / no evidence; "
                    "1 = partial or vague evidence; "
                    "2 = clear, specific evidence"
                ),
            },
            settings=settings,
        )
        user_prompt = load_and_render(
            USER_PROMPT_FILE,
            {
                "COMPANY_ID": company_id or "unknown",
                "COMPANY_NAME": company_name or "unknown",
                "SOURCE_TYPE": source_type or "unknown",
                "DOCUMENT_TEXT": prepared,
            },
            settings=settings,
        )
    except PromptLoadError as exc:
        logger.exception("Failed to load analysis prompts")
        result = DocumentAnalysisResult(
            company_id=company_id,
            company_name=company_name,
            source_type=source_type,
            document_path=document_path,
            model_id=default_model,
            prompt_version=PROMPT_VERSION,
            status="error",
            dimensions=empty_dimensions(),
            overall_confidence=0.0,
            metadata={"preparation": prep_meta},
            errors=[str(exc)],
        )
        if save:
            _persist(result, settings=settings)
        return result

    try:
        llm_client = client or get_llm_client(settings=settings)
        raw = llm_client.chat_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        result = _parse_model_payload(
            raw,
            company_id=company_id,
            company_name=company_name,
            source_type=source_type,
            document_path=document_path,
            model_id=llm_client.model_id,
            prep_meta=prep_meta,
        )
    except (LLMClientError, ValueError) as exc:
        logger.exception("AI analysis failed for company=%s", company_id)
        result = DocumentAnalysisResult(
            company_id=company_id,
            company_name=company_name,
            source_type=source_type,
            document_path=document_path,
            model_id=default_model,
            prompt_version=PROMPT_VERSION,
            status="error",
            dimensions=empty_dimensions(),
            overall_confidence=0.0,
            metadata={"preparation": prep_meta},
            errors=[str(exc)],
        )

    if save:
        _persist(result, settings=settings)
    return result


def analyze_document(
    path: str | Path,
    *,
    company_id: str | None = None,
    company_name: str | None = None,
    source_type: str | None = None,
    settings: Settings | None = None,
    client: LLMClient | None = None,
    save: bool = True,
) -> DocumentAnalysisResult:
    """Load a clean document from disk and run :func:`analyze_text`."""
    settings = settings or get_settings()
    default_model = (
        settings.gemini_model
        if (settings.llm_provider or "").lower() == "gemini"
        else settings.openai_model
    )
    try:
        text, file_meta = load_clean_text(path)
    except DocumentLoadError as exc:
        result = DocumentAnalysisResult(
            company_id=company_id,
            company_name=company_name,
            source_type=source_type,
            document_path=str(path),
            model_id=default_model,
            prompt_version=PROMPT_VERSION,
            status="error",
            dimensions=empty_dimensions(),
            overall_confidence=0.0,
            metadata={},
            errors=[str(exc)],
        )
        if save:
            _persist(result, settings=settings)
        return result

    return analyze_text(
        text,
        company_id=company_id or file_meta.get("company_id"),
        company_name=company_name or file_meta.get("company_name"),
        source_type=source_type or file_meta.get("source_type"),
        document_path=str(path),
        settings=settings,
        client=client,
        save=save,
    )


def _dimension_list_for_prompt() -> str:
    lines = [f"- {dim.value}: {label}" for dim, label in DIMENSION_LABELS.items()]
    return "\n".join(lines)


def _parse_model_payload(
    raw: dict[str, Any],
    *,
    company_id: str | None,
    company_name: str | None,
    source_type: str | None,
    document_path: str | None,
    model_id: str,
    prep_meta: dict[str, Any],
) -> DocumentAnalysisResult:
    raw_dims = raw.get("dimensions")
    if not isinstance(raw_dims, dict):
        raise ValueError("Model JSON missing 'dimensions' object")

    dimensions: dict[str, DimensionAssessment] = {}
    errors: list[str] = []

    for dim_id, label in DIMENSION_LABELS.items():
        key = dim_id.value
        item = raw_dims.get(key)
        if not isinstance(item, dict):
            errors.append(f"Missing dimension: {key}")
            dimensions[key] = DimensionAssessment(
                id=dim_id,
                label=label,
                score=0,
                confidence=0.0,
                rationale="Model omitted this dimension",
            )
            continue
        try:
            score = int(item.get("score", 0))
            confidence = float(item.get("confidence", 0.0))
            quotes = item.get("evidence_quotes") or item.get("evidence") or []
            if not isinstance(quotes, list):
                quotes = []
            dimensions[key] = DimensionAssessment(
                id=dim_id,
                label=label,
                score=max(0, min(2, score)),
                confidence=max(0.0, min(1.0, confidence)),
                evidence_quotes=[str(q) for q in quotes],
                rationale=str(item.get("rationale", "")).strip(),
            )
        except (TypeError, ValueError) as exc:
            errors.append(f"Invalid dimension payload for {key}: {exc}")
            dimensions[key] = DimensionAssessment(
                id=dim_id,
                label=label,
                score=0,
                confidence=0.0,
                rationale="Invalid model payload",
            )

    if "overall_confidence" in raw:
        overall = float(raw["overall_confidence"])
        overall = max(0.0, min(1.0, overall))
    else:
        vals = [d.confidence for d in dimensions.values()]
        overall = sum(vals) / len(vals) if vals else 0.0

    status = "success" if not errors else "partial"
    return DocumentAnalysisResult(
        schema_version=ANALYSIS_SCHEMA_VERSION,
        company_id=company_id,
        company_name=company_name,
        source_type=source_type,
        document_path=document_path,
        analyzed_at=datetime.now(timezone.utc),
        model_id=model_id,
        prompt_version=PROMPT_VERSION,
        status=status,
        dimensions=dimensions,
        overall_confidence=overall,
        metadata={
            "preparation": prep_meta,
            "model_notes": raw.get("notes"),
        },
        errors=errors,
    )


def _persist(result: DocumentAnalysisResult, *, settings: Settings) -> Path:
    """Write analysis JSON under ``data/processed/ai/``."""
    out_dir = settings.resolve(settings.data_dir / "processed" / "ai")
    if result.company_id:
        out_dir = out_dir / result.company_id
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    source = result.source_type or "document"
    path = out_dir / f"{stamp}_{source}_analysis.json"
    path.write_text(
        json.dumps(result.to_json_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    result.metadata["archived_json"] = str(path)
    # Re-write so archived_json is stored inside the file.
    path.write_text(
        json.dumps(result.to_json_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Wrote AI analysis JSON → %s", path)
    return path
