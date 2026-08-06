"""High-level collection orchestration returning standardized JSON documents."""

from __future__ import annotations

from typing import Any

from pasi.config.settings import Settings, get_settings
from pasi.ingest.archive import archive_document
from pasi.ingest.careers import CareersPageCollector
from pasi.ingest.companies import get_company
from pasi.ingest.earnings import EarningsTranscriptCollector
from pasi.ingest.employee_reviews import EmployeeReviewDatasetLoader
from pasi.ingest.schema import CollectedDocument, SourceType, error_document
from pasi.ingest.sec_10k import SecTenKCollector
from pasi.logging.setup import get_logger

logger = get_logger(__name__)


def collect_source(
    *,
    company_id: str,
    source: SourceType | str,
    settings: Settings | None = None,
    archive: bool = True,
    **kwargs: Any,
) -> CollectedDocument:
    """Collect one source for one company and optionally archive the JSON.

    Extra ``kwargs`` are forwarded to the underlying collector
    (e.g. ``file_path``, ``careers_url``, ``dataset_path``, ``filing_year``).
    """
    settings = settings or get_settings()
    source_type = SourceType(source) if isinstance(source, str) else source
    company = get_company(company_id, settings=settings)
    company_name = company.get("name")

    logger.info("Collecting %s for %s", source_type.value, company_id)

    raw_bytes: bytes | None = None
    raw_suffix = ".bin"

    if source_type is SourceType.TEN_K:
        document = SecTenKCollector().collect(
            company_id=company_id,
            company_name=company_name,
            ticker=kwargs.get("ticker", company.get("ticker")),
            cik=kwargs.get("cik", company.get("cik")),
            filing_year=kwargs.get("filing_year"),
        )
        text = document.content.get("text")
        if isinstance(text, str) and text:
            raw_bytes = text.encode("utf-8")
            raw_suffix = ".html" if document.content.get("format") == "html" else ".txt"

    elif source_type is SourceType.EARNINGS_CALL:
        document = EarningsTranscriptCollector().collect(
            company_id=company_id,
            company_name=company_name,
            file_path=kwargs.get("file_path"),
            source_url=kwargs.get("source_url"),
            fiscal_period=kwargs.get("fiscal_period"),
            call_date=kwargs.get("call_date"),
        )
        text = document.content.get("text")
        if isinstance(text, str) and text:
            raw_bytes = text.encode("utf-8")
            raw_suffix = ".txt"

    elif source_type is SourceType.EMPLOYEE_REVIEWS:
        dataset_path = kwargs.get("dataset_path", company.get("reviews_dataset_path"))
        if not dataset_path:
            document = error_document(
                source_type=SourceType.EMPLOYEE_REVIEWS,
                company_id=company_id,
                company_name=company_name,
                method="dataset_import",
                license_note=(
                    "Packaged employee-review dataset. Use only datasets whose "
                    "license permits research; do not scrape Glassdoor."
                ),
                message="dataset_path is required (CLI --dataset-path or companies.yaml)",
            )
        else:
            document = EmployeeReviewDatasetLoader().collect(
                company_id=company_id,
                company_name=company_name,
                dataset_path=dataset_path,
                company_filter=kwargs.get("company_filter", company_name),
                company_column=kwargs.get("company_column", "company"),
                text_column=kwargs.get("text_column", "review_text"),
                max_records=kwargs.get("max_records"),
                dataset_name=kwargs.get("dataset_name"),
                dataset_license=kwargs.get("dataset_license"),
            )

    elif source_type is SourceType.CAREERS:
        document = CareersPageCollector().collect(
            company_id=company_id,
            company_name=company_name,
            careers_url=kwargs.get("careers_url", company.get("careers_url")),
            file_path=kwargs.get("file_path"),
            allow_fetch=bool(kwargs.get("allow_fetch", False)),
            max_links=int(kwargs.get("max_links", 100)),
        )
        html = document.content.get("html")
        if isinstance(html, str) and html:
            raw_bytes = html.encode("utf-8")
            raw_suffix = ".html"

    else:  # pragma: no cover
        raise ValueError(f"Unsupported source: {source_type}")

    if archive:
        path = archive_document(
            document,
            settings=settings,
            raw_bytes=raw_bytes if document.status.value != "error" else None,
            raw_suffix=raw_suffix,
        )
        document.metadata["archived_json"] = str(path)

    return document


def collect_many(
    *,
    company_ids: list[str],
    sources: list[SourceType | str],
    settings: Settings | None = None,
    archive: bool = True,
    **kwargs: Any,
) -> list[CollectedDocument]:
    """Collect multiple companies × sources; continues on per-item failures."""
    results: list[CollectedDocument] = []
    for company_id in company_ids:
        for source in sources:
            try:
                results.append(
                    collect_source(
                        company_id=company_id,
                        source=source,
                        settings=settings,
                        archive=archive,
                        **kwargs,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unhandled collect failure for %s/%s", company_id, source)
                results.append(
                    error_document(
                        source_type=SourceType(source) if isinstance(source, str) else source,
                        company_id=company_id,
                        method="collect_many",
                        license_note="n/a",
                        message=str(exc),
                    )
                )
    return results
