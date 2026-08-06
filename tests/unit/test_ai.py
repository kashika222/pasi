"""Tests for the AI analysis module (OpenAI calls are mocked)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from pasi.ai.analyzer import analyze_document, analyze_text
from pasi.ai.document_loader import load_clean_text
from pasi.clean.text import prepare_filing_text
from pasi.ai.prompts import load_and_render, render_prompt
from pasi.ai.schema import DimensionId
from pasi.config.settings import Settings, get_settings


SAMPLE_MODEL_JSON = {
    "dimensions": {
        "leadership_commitment": {
            "score": 2,
            "confidence": 0.8,
            "evidence_quotes": ["Our CEO sponsors the analytics agenda"],
            "rationale": "Clear executive sponsorship language.",
        },
        "talent_investment": {
            "score": 1,
            "confidence": 0.6,
            "evidence_quotes": ["hiring data scientists"],
            "rationale": "Mentions hiring but limited detail.",
        },
        "innovation": {
            "score": 2,
            "confidence": 0.7,
            "evidence_quotes": ["launched an AI-powered recommendation engine"],
            "rationale": "Concrete product innovation.",
        },
        "analytics_strategy": {
            "score": 1,
            "confidence": 0.5,
            "evidence_quotes": ["data-driven decision making"],
            "rationale": "Generic analytics language.",
        },
        "ai_strategy": {
            "score": 2,
            "confidence": 0.75,
            "evidence_quotes": ["enterprise AI roadmap"],
            "rationale": "Explicit AI strategy mention.",
        },
        "digital_transformation": {
            "score": 0,
            "confidence": 0.7,
            "evidence_quotes": [],
            "rationale": "Not discussed.",
        },
    },
    "overall_confidence": 0.68,
    "notes": "ok",
}


def test_render_prompt_variables() -> None:
    rendered = render_prompt("Hello {{NAME}}", {"NAME": "PASI"})
    assert rendered == "Hello PASI"


def test_load_analysis_prompts() -> None:
    get_settings.cache_clear()
    system = load_and_render(
        "document_analysis_system_v1.txt",
        {
            "DIMENSION_LIST": "- leadership_commitment: Leadership Commitment",
            "SCORE_RUBRIC": "0/1/2",
        },
    )
    assert "Leadership Commitment" in system
    user = load_and_render(
        "document_analysis_user_v1.txt",
        {
            "COMPANY_ID": "netflix",
            "COMPANY_NAME": "Netflix",
            "SOURCE_TYPE": "ten_k",
            "DOCUMENT_TEXT": "sample text",
        },
    )
    assert "sample text" in user
    assert "leadership_commitment" in user


def test_load_clean_text_plain_and_json(tmp_path: Path) -> None:
    txt = tmp_path / "doc.txt"
    txt.write_text("Analytics strategy is a priority.", encoding="utf-8")
    text, meta = load_clean_text(txt)
    assert "Analytics" in text
    assert meta["loader"] == "plain_text"

    payload = {
        "company_id": "netflix",
        "company_name": "Netflix",
        "source_type": "ten_k",
        "content": {"text": "AI strategy and talent investment discussed."},
    }
    js = tmp_path / "doc.json"
    js.write_text(json.dumps(payload), encoding="utf-8")
    text2, meta2 = load_clean_text(js)
    assert "AI strategy" in text2
    assert meta2["company_id"] == "netflix"


def test_prepare_filing_prefers_narrative_over_xbrl_header() -> None:
    raw = (
        "<?xml version='1.0'?><html xmlns:xbrl='http://www.xbrl.org'>"
        + ("xbrl context xmlns " * 2000)
        + "</html>"
        + " Item 7. Management's Discussion and Analysis. "
        + "We invest in machine learning and analytics platforms for personalization. "
        * 50
    )
    text, meta = prepare_filing_text(raw, max_chars=2000)
    assert "machine learning" in text.lower()
    assert meta["was_html"] is True
    assert "item 7" in text.lower() or "management" in text.lower()


def test_prepare_text_truncation() -> None:
    text, meta = prepare_filing_text("abcdefghij", max_chars=4)
    assert len(text) <= 4
    assert meta["sent_char_count"] <= 4


def test_analyze_text_with_mocked_openai(tmp_path: Path) -> None:
    get_settings.cache_clear()
    settings = Settings(
        data_dir=tmp_path / "data",
        openai_api_key="test-key",
        openai_model="gpt-4o-mini",
    )
    client = MagicMock()
    client.model_id = "gpt-4o-mini"
    client.chat_json.return_value = SAMPLE_MODEL_JSON

    result = analyze_text(
        "Our CEO sponsors the analytics agenda and an enterprise AI roadmap.",
        company_id="netflix",
        company_name="Netflix",
        source_type="earnings_call",
        settings=settings,
        client=client,
        save=True,
    )
    assert result.status == "success"
    assert result.overall_confidence == 0.68
    assert set(result.dimensions) == {d.value for d in DimensionId}
    assert result.dimensions["leadership_commitment"].score == 2
    assert result.dimensions["leadership_commitment"].confidence == 0.8
    assert result.metadata.get("archived_json")
    assert Path(result.metadata["archived_json"]).exists()
    client.chat_json.assert_called_once()
    get_settings.cache_clear()


def test_analyze_document_empty_file(tmp_path: Path) -> None:
    get_settings.cache_clear()
    path = tmp_path / "empty.txt"
    path.write_text("   ", encoding="utf-8")
    settings = Settings(data_dir=tmp_path / "data", openai_api_key="test-key")
    result = analyze_document(path, company_id="x", settings=settings, save=False)
    assert result.status == "error"
    assert "empty" in result.errors[0].lower()
    get_settings.cache_clear()


def test_analyze_text_partial_when_dimension_missing(tmp_path: Path) -> None:
    get_settings.cache_clear()
    settings = Settings(data_dir=tmp_path / "data", openai_api_key="test-key")
    client = MagicMock()
    client.model_id = "gpt-4o-mini"
    incomplete = {
        "dimensions": {
            "leadership_commitment": {
                "score": 1,
                "confidence": 0.4,
                "evidence_quotes": [],
                "rationale": "weak",
            }
        },
        "overall_confidence": 0.4,
    }
    client.chat_json.return_value = incomplete
    result = analyze_text(
        "Some text about leadership.",
        company_id="ford",
        settings=settings,
        client=client,
        save=False,
    )
    assert result.status == "partial"
    assert len(result.errors) >= 1
    assert "talent_investment" in result.dimensions
    get_settings.cache_clear()
