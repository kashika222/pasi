"""Tests for analytical store and research-app services."""

from __future__ import annotations

import json
from pathlib import Path

from pasi.config.settings import Settings, get_settings
from pasi.services import company_profile, comparison_payload, export_dimension_csv
from pasi.store.builder import rebuild_store
from pasi.store.repository import StoreRepository


def test_rebuild_store_indexes_raw_documents(tmp_path: Path) -> None:
    get_settings.cache_clear()
    data_dir = tmp_path / "data"
    raw = data_dir / "raw" / "netflix" / "ten_k"
    raw.mkdir(parents=True)
    payload = {
        "schema_version": "1.0",
        "source_type": "ten_k",
        "company_id": "netflix",
        "company_name": "Netflix",
        "collected_at": "2026-08-06T00:00:00Z",
        "status": "success",
        "provenance": {
            "method": "sec_edgar_download",
            "license_note": "test",
            "url": "https://example.com/nflx",
            "content_sha256": "abc",
        },
        "metadata": {"filing_date": "2026-01-23"},
        "content": {"text": "analytics", "char_count": 9},
        "errors": [],
    }
    (raw / "doc.json").write_text(json.dumps(payload), encoding="utf-8")

    # Copy companies.yaml reference by using real configs via settings.configs_dir
    settings = Settings(
        data_dir=data_dir,
        duckdb_path=tmp_path / "db" / "test.duckdb",
        configs_dir=Path("configs"),
    )
    counts = rebuild_store(settings=settings)
    assert counts["companies"] == 10
    assert counts["documents"] == 1

    repo = StoreRepository(settings=settings)
    docs = repo.documents(company_id="netflix")
    assert len(docs) == 1
    assert docs.iloc[0]["provenance_url"] == "https://example.com/nflx"

    profile = company_profile(repo, "netflix")
    assert profile["has_documents"] is True
    assert profile["has_analysis"] is False
    assert all(cat["available"] is False for cat in profile["categories"])

    comp = comparison_payload(repo, ["netflix"])
    assert comp["has_data"] is False
    csv_text = export_dimension_csv(repo)
    assert "company_id" in csv_text
    get_settings.cache_clear()


def test_store_indexes_analysis_and_evidence(tmp_path: Path) -> None:
    get_settings.cache_clear()
    data_dir = tmp_path / "data"
    ai_dir = data_dir / "processed" / "ai" / "netflix"
    ai_dir.mkdir(parents=True)
    analysis = {
        "schema_version": "1.0",
        "company_id": "netflix",
        "company_name": "Netflix",
        "source_type": "ten_k",
        "document_path": "data/raw/netflix/ten_k/doc.json",
        "analyzed_at": "2026-08-06T12:00:00Z",
        "model_id": "gpt-4o-mini",
        "prompt_version": "document_analysis_v1",
        "status": "success",
        "overall_confidence": 0.7,
        "dimensions": {
            "leadership_commitment": {
                "id": "leadership_commitment",
                "label": "Leadership Commitment",
                "score": 2,
                "confidence": 0.8,
                "evidence_quotes": ["CEO sponsors analytics"],
                "rationale": "Clear sponsorship.",
            },
            "talent_investment": {
                "id": "talent_investment",
                "label": "Talent Investment",
                "score": 1,
                "confidence": 0.5,
                "evidence_quotes": [],
                "rationale": "Limited.",
            },
            "innovation": {
                "id": "innovation",
                "label": "Innovation",
                "score": 2,
                "confidence": 0.7,
                "evidence_quotes": ["recommendation engine"],
                "rationale": "Product signal.",
            },
            "analytics_strategy": {
                "id": "analytics_strategy",
                "label": "Analytics Strategy",
                "score": 1,
                "confidence": 0.6,
                "evidence_quotes": ["data-driven"],
                "rationale": "Generic.",
            },
            "ai_strategy": {
                "id": "ai_strategy",
                "label": "AI Strategy",
                "score": 2,
                "confidence": 0.7,
                "evidence_quotes": ["AI roadmap"],
                "rationale": "Explicit.",
            },
            "digital_transformation": {
                "id": "digital_transformation",
                "label": "Digital Transformation",
                "score": 0,
                "confidence": 0.6,
                "evidence_quotes": [],
                "rationale": "Absent.",
            },
        },
        "metadata": {},
        "errors": [],
    }
    (ai_dir / "20260806T120000Z_ten_k_analysis.json").write_text(
        json.dumps(analysis), encoding="utf-8"
    )

    settings = Settings(
        data_dir=data_dir,
        duckdb_path=tmp_path / "db" / "test2.duckdb",
        configs_dir=Path("configs"),
    )
    counts = rebuild_store(settings=settings)
    assert counts["analyses"] == 1
    assert counts["dimension_scores"] == 6
    assert counts["evidence_items"] >= 3

    repo = StoreRepository(settings=settings)
    profile = company_profile(repo, "netflix")
    assert profile["has_analysis"] is True
    leadership = next(c for c in profile["categories"] if c["id"] == "leadership_commitment")
    assert leadership["available"] is True
    assert leadership["score"] == 2

    comp = comparison_payload(repo, ["netflix"])
    assert comp["has_data"] is True
    assert "Netflix" in comp["radar"]
    get_settings.cache_clear()
