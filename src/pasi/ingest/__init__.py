"""Public ingest API."""

from pasi.ingest.archive import archive_document
from pasi.ingest.careers import CareersPageCollector
from pasi.ingest.collect import collect_many, collect_source
from pasi.ingest.earnings import EarningsTranscriptCollector
from pasi.ingest.employee_reviews import EmployeeReviewDatasetLoader
from pasi.ingest.schema import (
    SCHEMA_VERSION,
    CollectedDocument,
    CollectionStatus,
    Provenance,
    SourceType,
)
from pasi.ingest.sec_10k import SecTenKCollector

__all__ = [
    "SCHEMA_VERSION",
    "CollectedDocument",
    "CollectionStatus",
    "Provenance",
    "SourceType",
    "SecTenKCollector",
    "EarningsTranscriptCollector",
    "EmployeeReviewDatasetLoader",
    "CareersPageCollector",
    "archive_document",
    "collect_source",
    "collect_many",
]
