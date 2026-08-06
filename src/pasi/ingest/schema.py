"""Standardized collection output schema for all PASI data sources.

Every collector returns a :class:`CollectedDocument` that serializes to JSON
with a stable shape so downstream cleaning / NLP / scoring stay source-agnostic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


SCHEMA_VERSION = "1.0"


class SourceType(str, Enum):
    """Supported public evidence source types."""

    TEN_K = "ten_k"
    EARNINGS_CALL = "earnings_call"
    EMPLOYEE_REVIEWS = "employee_reviews"
    CAREERS = "careers"


class CollectionStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"


class Provenance(BaseModel):
    """Where the artifact came from and how it was obtained."""

    method: str = Field(
        ...,
        description="Collection method, e.g. sec_edgar_download, local_file, http_get",
    )
    license_note: str = Field(
        ...,
        description="License / ToS note for reuse and publication",
    )
    url: str | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content_sha256: str | None = None
    local_path: str | None = None
    http_status: int | None = None


class CollectedDocument(BaseModel):
    """Canonical JSON envelope returned by every ingest collector."""

    schema_version: str = SCHEMA_VERSION
    source_type: SourceType
    company_id: str
    company_name: str | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: CollectionStatus
    provenance: Provenance
    metadata: dict[str, Any] = Field(default_factory=dict)
    content: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        """JSON-ready dict (datetimes as ISO-8601 strings)."""
        return self.model_dump(mode="json")


def error_document(
    *,
    source_type: SourceType,
    company_id: str,
    method: str,
    license_note: str,
    message: str,
    company_name: str | None = None,
    url: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> CollectedDocument:
    """Build a failed collection result without raising to the caller."""
    return CollectedDocument(
        source_type=source_type,
        company_id=company_id,
        company_name=company_name,
        status=CollectionStatus.ERROR,
        provenance=Provenance(method=method, license_note=license_note, url=url),
        metadata=metadata or {},
        content={},
        errors=[message],
    )
