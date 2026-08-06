"""Load packaged employee-review datasets (no Glassdoor scraping).

Expected input is a licensed CSV / JSON / JSONL / Parquet file under
``data/external/`` (or any path you pass). Rows are optionally filtered to a
company name / ticker column configured by the caller.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from pasi.ingest.http import sha256_bytes
from pasi.ingest.schema import (
    CollectedDocument,
    CollectionStatus,
    Provenance,
    SourceType,
    error_document,
)
from pasi.logging.setup import get_logger

logger = get_logger(__name__)

LICENSE_NOTE = (
    "Packaged employee-review dataset. Use only datasets whose license permits "
    "research; do not scrape Glassdoor or similar sites."
)


class EmployeeReviewDatasetLoader:
    """Import employee review rows into the standard collection envelope."""

    SUPPORTED_SUFFIXES = {".csv", ".json", ".jsonl", ".parquet"}

    def collect(
        self,
        *,
        company_id: str,
        dataset_path: str | Path,
        company_name: str | None = None,
        company_filter: str | None = None,
        company_column: str = "company",
        text_column: str | None = "review_text",
        max_records: int | None = None,
        dataset_name: str | None = None,
        dataset_license: str | None = None,
    ) -> CollectedDocument:
        """Load and optionally filter review records from a local dataset file."""
        method = "dataset_import"
        path = Path(dataset_path)
        license_note = dataset_license or LICENSE_NOTE

        if not path.exists():
            return error_document(
                source_type=SourceType.EMPLOYEE_REVIEWS,
                company_id=company_id,
                company_name=company_name,
                method=method,
                license_note=license_note,
                message=f"Dataset not found: {path}",
            )

        if path.suffix.lower() not in self.SUPPORTED_SUFFIXES:
            return error_document(
                source_type=SourceType.EMPLOYEE_REVIEWS,
                company_id=company_id,
                company_name=company_name,
                method=method,
                license_note=license_note,
                message=(
                    f"Unsupported dataset format '{path.suffix}'. "
                    f"Supported: {sorted(self.SUPPORTED_SUFFIXES)}"
                ),
            )

        try:
            raw = path.read_bytes()
            records = self._read_records(path)
            before = len(records)

            if company_filter:
                records = [
                    row
                    for row in records
                    if str(row.get(company_column, "")).strip().lower()
                    == company_filter.strip().lower()
                ]

            truncated = False
            if max_records is not None and len(records) > max_records:
                records = records[:max_records]
                truncated = True

            # Keep payloads portable: stringify values.
            normalized = [_normalize_record(row, text_column=text_column) for row in records]

            status = (
                CollectionStatus.SUCCESS
                if normalized
                else CollectionStatus.PARTIAL if before else CollectionStatus.ERROR
            )
            errors: list[str] = []
            if before == 0:
                errors.append("Dataset contained zero rows")
            elif not normalized:
                errors.append(
                    f"No rows matched company_filter={company_filter!r} "
                    f"on column={company_column!r}"
                )
            if truncated:
                errors.append(f"Truncated to max_records={max_records}")

            return CollectedDocument(
                source_type=SourceType.EMPLOYEE_REVIEWS,
                company_id=company_id,
                company_name=company_name,
                status=status,
                provenance=Provenance(
                    method=method,
                    license_note=license_note,
                    url=path.resolve().as_uri(),
                    content_sha256=sha256_bytes(raw),
                    local_path=str(path),
                ),
                metadata={
                    "dataset_path": str(path),
                    "dataset_name": dataset_name or path.name,
                    "company_column": company_column,
                    "company_filter": company_filter,
                    "text_column": text_column,
                    "rows_before_filter": before,
                    "rows_returned": len(normalized),
                    "truncated": truncated,
                },
                content={
                    "record_count": len(normalized),
                    "records": normalized,
                    "columns": sorted({key for row in normalized for key in row}),
                },
                errors=errors,
            )
        except Exception as exc:  # noqa: BLE001 — surface as envelope error
            logger.exception("Employee review load failed for %s", company_id)
            return error_document(
                source_type=SourceType.EMPLOYEE_REVIEWS,
                company_id=company_id,
                company_name=company_name,
                method=method,
                license_note=license_note,
                message=str(exc),
                metadata={"dataset_path": str(path)},
            )

    def _read_records(self, path: Path) -> list[dict[str, Any]]:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            with path.open(newline="", encoding="utf-8", errors="replace") as handle:
                return list(csv.DictReader(handle))
        if suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return [dict(row) for row in payload]
            if isinstance(payload, dict) and "records" in payload:
                return [dict(row) for row in payload["records"]]
            raise ValueError("JSON dataset must be a list or contain a 'records' array")
        if suffix == ".jsonl":
            rows: list[dict[str, Any]] = []
            with path.open(encoding="utf-8", errors="replace") as handle:
                for line_no, line in enumerate(handle, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    item = json.loads(line)
                    if not isinstance(item, dict):
                        raise ValueError(f"JSONL line {line_no} is not an object")
                    rows.append(item)
            return rows
        if suffix == ".parquet":
            try:
                import pandas as pd
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError(
                    "pandas is required to read parquet review datasets"
                ) from exc
            frame = pd.read_parquet(path)
            return frame.to_dict(orient="records")
        raise ValueError(f"Unsupported suffix: {suffix}")


def _normalize_record(
    row: dict[str, Any],
    *,
    text_column: str | None,
) -> dict[str, Any]:
    normalized = {str(key): _stringify(value) for key, value in row.items()}
    if text_column and text_column in normalized:
        normalized["review_text"] = normalized[text_column]
    return normalized


def _stringify(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
