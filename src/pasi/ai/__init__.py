"""AI-assisted document analysis package."""

from pasi.ai.analyzer import analyze_document, analyze_text
from pasi.ai.schema import (
    ANALYSIS_SCHEMA_VERSION,
    DIMENSION_LABELS,
    DimensionAssessment,
    DimensionId,
    DocumentAnalysisResult,
)

__all__ = [
    "ANALYSIS_SCHEMA_VERSION",
    "DIMENSION_LABELS",
    "DimensionAssessment",
    "DimensionId",
    "DocumentAnalysisResult",
    "analyze_document",
    "analyze_text",
]
