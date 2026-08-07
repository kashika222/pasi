"""DuckDB analytical store for PASI research application.

Indexes pipeline artifacts (raw collections + AI analyses) into queryable tables.
Never invents scores — only persists what the pipeline produced.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from pasi.ai.schema import DIMENSION_LABELS
from pasi.config.settings import Settings, get_settings
from pasi.ingest.companies import load_companies
from pasi.logging.setup import get_logger

logger = get_logger(__name__)


def _is_streamlit_cloud() -> bool:
    """Streamlit Community Cloud mounts the repo under ``/mount/src``."""
    return Path("/mount/src").exists() or os.environ.get("STREAMLIT_RUNTIME_ENV") == "cloud"

DDL = """
CREATE TABLE IF NOT EXISTS companies (
    company_id VARCHAR PRIMARY KEY,
    name VARCHAR,
    ticker VARCHAR,
    segment VARCHAR,
    industry VARCHAR,
    proxy_label VARCHAR,
    careers_url VARCHAR,
    notes VARCHAR
);

CREATE TABLE IF NOT EXISTS documents (
    doc_id VARCHAR PRIMARY KEY,
    company_id VARCHAR,
    source_type VARCHAR,
    status VARCHAR,
    collected_at VARCHAR,
    filing_date VARCHAR,
    provenance_url VARCHAR,
    provenance_method VARCHAR,
    local_json_path VARCHAR,
    char_count BIGINT,
    content_sha256 VARCHAR,
    metadata_json VARCHAR
);

CREATE TABLE IF NOT EXISTS analyses (
    analysis_id VARCHAR PRIMARY KEY,
    company_id VARCHAR,
    source_type VARCHAR,
    document_path VARCHAR,
    analyzed_at VARCHAR,
    model_id VARCHAR,
    prompt_version VARCHAR,
    status VARCHAR,
    overall_confidence DOUBLE,
    local_json_path VARCHAR,
    metadata_json VARCHAR
);

CREATE TABLE IF NOT EXISTS dimension_scores (
    analysis_id VARCHAR,
    company_id VARCHAR,
    source_type VARCHAR,
    dimension_id VARCHAR,
    dimension_label VARCHAR,
    score INTEGER,
    confidence DOUBLE,
    rationale VARCHAR,
    evidence_json VARCHAR,
    PRIMARY KEY (analysis_id, dimension_id)
);

CREATE TABLE IF NOT EXISTS evidence_items (
    evidence_id VARCHAR PRIMARY KEY,
    analysis_id VARCHAR,
    company_id VARCHAR,
    source_type VARCHAR,
    dimension_id VARCHAR,
    excerpt VARCHAR,
    rationale VARCHAR,
    score INTEGER,
    confidence DOUBLE,
    document_path VARCHAR,
    provenance_url VARCHAR
);

CREATE TABLE IF NOT EXISTS pipeline_meta (
    key VARCHAR PRIMARY KEY,
    value VARCHAR
);
"""


def duckdb_path(settings: Settings | None = None) -> Path:
    """Resolve DuckDB file location.

    On Streamlit Cloud, prefer ``/tmp/pasi.duckdb``. The repo mount often breaks
    DuckDB file locks / read-only opens under ``db/``.
    """
    settings = settings or get_settings()
    configured = Path(getattr(settings, "duckdb_path", None) or Path("db/pasi.duckdb"))
    if configured.is_absolute():
        return configured
    if _is_streamlit_cloud():
        return Path("/tmp/pasi.duckdb")
    return settings.resolve(configured)


def connect(settings: Settings | None = None, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    path = duckdb_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Read-only opens fail on some cloud mounts even when the file exists.
    if read_only and not path.exists():
        read_only = False
    try:
        return duckdb.connect(str(path), read_only=read_only)
    except duckdb.Error:
        if read_only:
            logger.warning("DuckDB read-only open failed for %s; retrying read-write", path)
            return duckdb.connect(str(path), read_only=False)
        raise


def rebuild_store(settings: Settings | None = None) -> dict[str, int]:
    """Scan ``data/raw`` and ``data/processed/ai`` and rebuild the DuckDB mart."""
    settings = settings or get_settings()
    path = duckdb_path(settings)
    if path.exists():
        path.unlink()

    con = connect(settings=settings, read_only=False)
    try:
        con.execute(DDL)
        counts = {
            "companies": _load_companies(con, settings),
            "documents": _load_documents(con, settings),
            "analyses": 0,
            "dimension_scores": 0,
            "evidence_items": 0,
        }
        a_counts = _load_analyses(con, settings)
        counts.update(a_counts)
        con.execute("DELETE FROM pipeline_meta")
        con.execute(
            "INSERT INTO pipeline_meta VALUES ('built_at', ?), ('schema_version', '1.0')",
            [datetime.now(timezone.utc).isoformat()],
        )
        logger.info("Rebuilt PASI store at %s (%s)", path, counts)
        return counts
    finally:
        con.close()


def _load_companies(con: duckdb.DuckDBPyConnection, settings: Settings) -> int:
    rows = load_companies(settings=settings)
    for row in rows:
        con.execute(
            """
            INSERT INTO companies
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row.get("id"),
                row.get("name"),
                row.get("ticker"),
                row.get("segment"),
                row.get("industry"),
                row.get("proxy_label"),
                row.get("careers_url"),
                row.get("notes"),
            ],
        )
    return len(rows)


def _load_documents(con: duckdb.DuckDBPyConnection, settings: Settings) -> int:
    """Load documents from local raw JSON and/or slim deploy catalog."""
    count = 0
    seen: set[str] = set()

    def _insert(row: dict[str, Any]) -> None:
        nonlocal count
        doc_id = str(row["doc_id"])
        if doc_id in seen:
            return
        seen.add(doc_id)
        con.execute(
            """
            INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row["doc_id"],
                row["company_id"],
                row["source_type"],
                row.get("status"),
                row.get("collected_at"),
                row.get("filing_date"),
                row.get("provenance_url"),
                row.get("provenance_method"),
                row.get("local_json_path"),
                row.get("char_count"),
                row.get("content_sha256"),
                json.dumps(row.get("metadata") or {}),
            ],
        )
        count += 1

    raw_root = settings.resolve(settings.data_dir / "raw")
    if raw_root.exists():
        for json_path in sorted(raw_root.rglob("*.json")):
            if json_path.name.endswith("_analysis.json"):
                continue
            try:
                payload = json.loads(json_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Skipping unreadable document %s: %s", json_path, exc)
                continue
            if not isinstance(payload, dict) or "source_type" not in payload:
                continue
            if payload.get("status") == "error":
                logger.info("Skipping error collection envelope %s", json_path)
                continue
            company_id = payload.get("company_id") or json_path.parent.parent.name
            source_type = payload.get("source_type")
            provenance = payload.get("provenance") or {}
            content = payload.get("content") or {}
            metadata = payload.get("metadata") or {}
            _insert(
                {
                    "doc_id": f"{company_id}:{source_type}:{json_path.stem}",
                    "company_id": company_id,
                    "source_type": source_type,
                    "status": payload.get("status"),
                    "collected_at": payload.get("collected_at"),
                    "filing_date": metadata.get("filing_date") or metadata.get("call_date"),
                    "provenance_url": provenance.get("url"),
                    "provenance_method": provenance.get("method"),
                    "local_json_path": str(json_path),
                    "char_count": content.get("char_count"),
                    "content_sha256": provenance.get("content_sha256"),
                    "metadata": metadata,
                }
            )

    # Slim catalog used on Streamlit Cloud (no full filing text in git).
    catalog = settings.resolve(settings.data_dir / "catalog" / "documents.jsonl")
    if catalog.exists():
        with catalog.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    logger.warning("Bad catalog line %s: %s", line_no, exc)
                    continue
                company_id = record.get("company_id")
                source_type = record.get("source_type")
                if not company_id or not source_type:
                    continue
                stem = Path(str(record.get("local_json_path") or f"{company_id}_{source_type}")).stem
                _insert(
                    {
                        "doc_id": f"{company_id}:{source_type}:{stem}",
                        "company_id": company_id,
                        "source_type": source_type,
                        "status": record.get("status"),
                        "collected_at": record.get("collected_at"),
                        "filing_date": record.get("filing_date"),
                        "provenance_url": record.get("provenance_url"),
                        "provenance_method": record.get("provenance_method"),
                        "local_json_path": record.get("local_json_path"),
                        "char_count": record.get("char_count"),
                        "content_sha256": record.get("content_sha256"),
                        "metadata": record.get("metadata") or {},
                    }
                )

    return count


def _load_analyses(con: duckdb.DuckDBPyConnection, settings: Settings) -> dict[str, int]:
    ai_root = settings.resolve(settings.data_dir / "processed" / "ai")
    counts = {"analyses": 0, "dimension_scores": 0, "evidence_items": 0}
    if not ai_root.exists():
        return counts

    label_lookup = {d.value: label for d, label in DIMENSION_LABELS.items()}

    for json_path in sorted(ai_root.rglob("*_analysis.json")):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Skipping unreadable analysis %s: %s", json_path, exc)
            continue
        if not isinstance(payload, dict) or "dimensions" not in payload:
            continue
        if payload.get("status") == "error":
            logger.info("Skipping error analysis envelope %s", json_path)
            continue

        company_id = payload.get("company_id") or json_path.parent.name
        source_type = payload.get("source_type") or "unknown"
        analysis_id = f"{company_id}:{source_type}:{json_path.stem}"
        con.execute(
            """
            INSERT INTO analyses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                analysis_id,
                company_id,
                source_type,
                payload.get("document_path"),
                payload.get("analyzed_at"),
                payload.get("model_id"),
                payload.get("prompt_version"),
                payload.get("status"),
                payload.get("overall_confidence"),
                str(json_path),
                json.dumps(payload.get("metadata") or {}),
            ],
        )
        counts["analyses"] += 1

        dimensions = payload.get("dimensions") or {}
        # Resolve provenance URL from matching document when possible.
        provenance_url = _lookup_doc_url(con, company_id, source_type)

        for dim_key, dim_val in dimensions.items():
            if not isinstance(dim_val, dict):
                continue
            label = dim_val.get("label") or label_lookup.get(dim_key, dim_key)
            score = dim_val.get("score")
            confidence = dim_val.get("confidence")
            rationale = dim_val.get("rationale") or ""
            quotes = dim_val.get("evidence_quotes") or []
            con.execute(
                """
                INSERT INTO dimension_scores VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    analysis_id,
                    company_id,
                    source_type,
                    dim_key,
                    label,
                    score,
                    confidence,
                    rationale,
                    json.dumps(quotes),
                ],
            )
            counts["dimension_scores"] += 1

            for idx, quote in enumerate(quotes):
                if not isinstance(quote, str) or not quote.strip():
                    continue
                evidence_id = f"{analysis_id}:{dim_key}:{idx}"
                con.execute(
                    """
                    INSERT INTO evidence_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        evidence_id,
                        analysis_id,
                        company_id,
                        source_type,
                        dim_key,
                        quote.strip(),
                        rationale,
                        score,
                        confidence,
                        payload.get("document_path"),
                        provenance_url,
                    ],
                )
                counts["evidence_items"] += 1

    return counts


def _lookup_doc_url(
    con: duckdb.DuckDBPyConnection,
    company_id: str,
    source_type: str,
) -> str | None:
    row = con.execute(
        """
        SELECT provenance_url FROM documents
        WHERE company_id = ? AND source_type = ?
        ORDER BY collected_at DESC NULLS LAST
        LIMIT 1
        """,
        [company_id, source_type],
    ).fetchone()
    return row[0] if row else None


def ensure_store(settings: Settings | None = None) -> Path:
    """Rebuild store if missing or unreadable; return path."""
    settings = settings or get_settings()
    path = duckdb_path(settings)
    if not path.exists():
        rebuild_store(settings=settings)
        return path
    try:
        con = connect(settings=settings, read_only=False)
        try:
            con.execute("SELECT 1 FROM pipeline_meta LIMIT 1")
        finally:
            con.close()
    except duckdb.Error as exc:
        logger.warning("Existing DuckDB store unreadable (%s); rebuilding", exc)
        rebuild_store(settings=settings)
    return path
