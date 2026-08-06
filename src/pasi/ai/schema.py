"""Structured output schema for AI document analysis."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


ANALYSIS_SCHEMA_VERSION = "1.0"


class DimensionId(str, Enum):
    """Analytics-maturity signal dimensions extracted per document."""

    LEADERSHIP_COMMITMENT = "leadership_commitment"
    TALENT_INVESTMENT = "talent_investment"
    INNOVATION = "innovation"
    ANALYTICS_STRATEGY = "analytics_strategy"
    AI_STRATEGY = "ai_strategy"
    DIGITAL_TRANSFORMATION = "digital_transformation"


DIMENSION_LABELS: dict[DimensionId, str] = {
    DimensionId.LEADERSHIP_COMMITMENT: "Leadership Commitment",
    DimensionId.TALENT_INVESTMENT: "Talent Investment",
    DimensionId.INNOVATION: "Innovation",
    DimensionId.ANALYTICS_STRATEGY: "Analytics Strategy",
    DimensionId.AI_STRATEGY: "AI Strategy",
    DimensionId.DIGITAL_TRANSFORMATION: "Digital Transformation",
}


class DimensionAssessment(BaseModel):
    """Assessment of one maturity-related dimension."""

    id: DimensionId
    label: str
    score: int = Field(..., ge=0, le=2, description="0=absent, 1=partial, 2=strong")
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_quotes: list[str] = Field(default_factory=list)
    rationale: str = ""

    @field_validator("evidence_quotes")
    @classmethod
    def _limit_quotes(cls, value: list[str]) -> list[str]:
        cleaned = [q.strip() for q in value if isinstance(q, str) and q.strip()]
        return cleaned[:5]


class DocumentAnalysisResult(BaseModel):
    """Canonical JSON envelope returned by the AI analysis module."""

    schema_version: str = ANALYSIS_SCHEMA_VERSION
    company_id: str | None = None
    company_name: str | None = None
    source_type: str | None = None
    document_path: str | None = None
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_id: str
    prompt_version: str
    status: str = Field(description="success | partial | error")
    dimensions: dict[str, DimensionAssessment] = Field(default_factory=dict)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def empty_dimensions() -> dict[str, DimensionAssessment]:
    """Return zeroed assessments for all required dimensions."""
    result: dict[str, DimensionAssessment] = {}
    for dim_id, label in DIMENSION_LABELS.items():
        result[dim_id.value] = DimensionAssessment(
            id=dim_id,
            label=label,
            score=0,
            confidence=0.0,
            evidence_quotes=[],
            rationale="Not assessed",
        )
    return result
