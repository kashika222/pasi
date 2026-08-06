"""Collect earnings call transcripts from local archives or explicit URLs.

PASI does **not** scrape commercial transcript sites by default. Preferred path:

1. Manually download a transcript you are allowed to keep.
2. Pass the local path to :meth:`EarningsTranscriptCollector.collect`.

Optional ``source_url`` fetches only when the caller explicitly provides a URL
they are authorized to retrieve.
"""

from __future__ import annotations

from pathlib import Path

from pasi.ingest.http import HttpClient, HttpError, sha256_bytes, sha256_text
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
    "Caller-supplied earnings transcript. Ensure redistribution rights / ToS "
    "allow research use before archiving or publishing excerpts."
)


class EarningsTranscriptCollector:
    """Load an earnings transcript into the standard collection envelope."""

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or HttpClient()

    def collect(
        self,
        *,
        company_id: str,
        company_name: str | None = None,
        file_path: str | Path | None = None,
        source_url: str | None = None,
        fiscal_period: str | None = None,
        call_date: str | None = None,
    ) -> CollectedDocument:
        """Collect transcript text from a local file and/or an explicit URL.

        Exactly one of ``file_path`` or ``source_url`` is required.
        """
        method = "local_file" if file_path else "http_get"
        if bool(file_path) == bool(source_url):
            return error_document(
                source_type=SourceType.EARNINGS_CALL,
                company_id=company_id,
                company_name=company_name,
                method=method,
                license_note=LICENSE_NOTE,
                message="Provide exactly one of file_path or source_url",
                metadata={"fiscal_period": fiscal_period, "call_date": call_date},
            )

        try:
            if file_path is not None:
                path = Path(file_path)
                if not path.exists():
                    raise FileNotFoundError(f"Transcript file not found: {path}")
                raw = path.read_bytes()
                text = raw.decode("utf-8", errors="replace")
                url = path.resolve().as_uri()
                http_status = None
                method = "local_file"
                sha = sha256_bytes(raw)
            else:
                assert source_url is not None
                logger.info("Downloading earnings transcript from %s", source_url)
                response = self.client.get(source_url)
                raw = response.content
                text = raw.decode("utf-8", errors="replace")
                url = source_url
                http_status = response.status_code
                method = "http_get"
                sha = sha256_bytes(raw)

            status = CollectionStatus.SUCCESS if text.strip() else CollectionStatus.PARTIAL
            errors: list[str] = []
            if not text.strip():
                errors.append("Transcript text is empty")

            return CollectedDocument(
                source_type=SourceType.EARNINGS_CALL,
                company_id=company_id,
                company_name=company_name,
                status=status,
                provenance=Provenance(
                    method=method,
                    license_note=LICENSE_NOTE,
                    url=url,
                    content_sha256=sha,
                    http_status=http_status,
                    local_path=str(file_path) if file_path else None,
                ),
                metadata={
                    "fiscal_period": fiscal_period,
                    "call_date": call_date,
                    "source_path": str(file_path) if file_path else None,
                },
                content={
                    "text": text,
                    "format": _guess_format(file_path, source_url),
                    "char_count": len(text),
                    "sha256": sha256_text(text),
                },
                errors=errors,
            )
        except (OSError, HttpError, UnicodeError) as exc:
            logger.exception("Earnings transcript collection failed for %s", company_id)
            return error_document(
                source_type=SourceType.EARNINGS_CALL,
                company_id=company_id,
                company_name=company_name,
                method=method,
                license_note=LICENSE_NOTE,
                message=str(exc),
                url=source_url,
                metadata={"fiscal_period": fiscal_period, "call_date": call_date},
            )


def _guess_format(file_path: str | Path | None, source_url: str | None) -> str:
    name = str(file_path or source_url or "").lower()
    if name.endswith(".pdf"):
        return "pdf"
    if name.endswith(".html") or name.endswith(".htm"):
        return "html"
    if name.endswith(".json"):
        return "json"
    return "text"
