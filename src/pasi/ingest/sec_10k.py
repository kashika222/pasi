"""Download Form 10-K filings from the SEC EDGAR APIs.

Uses only official SEC endpoints:

* ``https://www.sec.gov/files/company_tickers.json``
* ``https://data.sec.gov/submissions/CIK##########.json``
* ``https://www.sec.gov/Archives/edgar/data/...``

SEC requires a descriptive ``User-Agent`` with contact info
(configured via ``PASI_SEC_USER_AGENT``).
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from pasi.ingest.http import HttpClient, HttpError, sha256_bytes
from pasi.ingest.schema import (
    CollectedDocument,
    CollectionStatus,
    Provenance,
    SourceType,
    error_document,
)
from pasi.logging.setup import get_logger

logger = get_logger(__name__)

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVES_URL = (
    "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_nodash}/{primary_document}"
)

LICENSE_NOTE = (
    "SEC EDGAR public filing. Reuse subject to SEC terms of use; "
    "provide a descriptive User-Agent with contact email."
)


class SecTenKCollector:
    """Collect the latest (or year-filtered) Form 10-K for a ticker."""

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or HttpClient()

    def collect(
        self,
        *,
        company_id: str,
        company_name: str | None = None,
        ticker: str | None = None,
        cik: str | None = None,
        filing_year: int | None = None,
    ) -> CollectedDocument:
        """Download a 10-K and return a standardized JSON document.

        Parameters
        ----------
        company_id:
            Internal PASI company id.
        ticker:
            Equity ticker used to resolve CIK when ``cik`` is omitted.
        cik:
            Optional SEC CIK (with or without leading zeros).
        filing_year:
            If set, prefer a 10-K whose filing date starts with this year.
        """
        method = "sec_edgar_download"
        if not ticker and not cik:
            return error_document(
                source_type=SourceType.TEN_K,
                company_id=company_id,
                company_name=company_name,
                method=method,
                license_note=LICENSE_NOTE,
                message="ticker or cik is required to download a 10-K",
            )

        try:
            resolved_cik = self._normalize_cik(cik) if cik else self.resolve_cik(ticker or "")
            filing = self._select_10k(resolved_cik, filing_year=filing_year)
            raw_bytes, source_url = self._download_primary_document(resolved_cik, filing)
            text = self._bytes_to_text(raw_bytes)

            status = CollectionStatus.SUCCESS if text.strip() else CollectionStatus.PARTIAL
            errors: list[str] = []
            if not text.strip():
                errors.append("Downloaded filing was empty after text decoding")

            return CollectedDocument(
                source_type=SourceType.TEN_K,
                company_id=company_id,
                company_name=company_name,
                status=status,
                provenance=Provenance(
                    method=method,
                    license_note=LICENSE_NOTE,
                    url=source_url,
                    content_sha256=sha256_bytes(raw_bytes),
                    http_status=200,
                ),
                metadata={
                    "ticker": ticker,
                    "cik": resolved_cik,
                    "form": filing.get("form"),
                    "accession_number": filing.get("accessionNumber"),
                    "filing_date": filing.get("filingDate"),
                    "report_date": filing.get("reportDate"),
                    "primary_document": filing.get("primaryDocument"),
                    "filing_year_filter": filing_year,
                },
                content={
                    "text": text,
                    "format": self._infer_format(filing.get("primaryDocument", "")),
                    "char_count": len(text),
                },
                errors=errors,
            )
        except (HttpError, KeyError, ValueError, OSError) as exc:
            logger.exception("SEC 10-K collection failed for %s", company_id)
            return error_document(
                source_type=SourceType.TEN_K,
                company_id=company_id,
                company_name=company_name,
                method=method,
                license_note=LICENSE_NOTE,
                message=str(exc),
                metadata={"ticker": ticker, "cik": cik, "filing_year": filing_year},
            )

    def resolve_cik(self, ticker: str) -> str:
        """Map a ticker symbol to a zero-padded 10-digit CIK."""
        ticker_key = ticker.strip().upper()
        mapping = _load_ticker_cik_map(self.client)
        if ticker_key not in mapping:
            raise ValueError(f"Ticker not found in SEC company_tickers.json: {ticker_key}")
        return mapping[ticker_key]

    def _select_10k(self, cik: str, *, filing_year: int | None) -> dict[str, Any]:
        url = SUBMISSIONS_URL.format(cik=cik)
        payload = self.client.get(url, expect_json=True).json()
        recent = payload.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        candidates: list[dict[str, Any]] = []
        # Include 20-F for foreign private issuers (e.g. Spotify).
        accepted = {"10-K", "10-K/A", "20-F", "20-F/A"}
        for idx, form in enumerate(forms):
            if form not in accepted:
                continue
            filing = {
                "form": form,
                "accessionNumber": recent["accessionNumber"][idx],
                "filingDate": recent["filingDate"][idx],
                "reportDate": recent.get("reportDate", [None] * len(forms))[idx],
                "primaryDocument": recent["primaryDocument"][idx],
            }
            if filing_year is not None and not str(filing["filingDate"]).startswith(
                str(filing_year)
            ):
                continue
            candidates.append(filing)

        if not candidates:
            year_msg = f" for filing year {filing_year}" if filing_year else ""
            raise ValueError(f"No 10-K/20-F filings found for CIK {cik}{year_msg}")

        # Prefer original annual forms over amendments; filings are newest-first.
        preferred_order = ["10-K", "20-F", "10-K/A", "20-F/A"]
        for form_name in preferred_order:
            matched = [c for c in candidates if c["form"] == form_name]
            if matched:
                return matched[0]
        return candidates[0]

    def _download_primary_document(
        self,
        cik: str,
        filing: dict[str, Any],
    ) -> tuple[bytes, str]:
        accession = str(filing["accessionNumber"])
        accession_nodash = accession.replace("-", "")
        primary = str(filing["primaryDocument"])
        cik_int = str(int(cik))  # archives path drops leading zeros
        url = ARCHIVES_URL.format(
            cik_int=cik_int,
            accession_nodash=accession_nodash,
            primary_document=primary,
        )
        response = self.client.get(url)
        return response.content, url

    @staticmethod
    def _normalize_cik(cik: str) -> str:
        digits = re.sub(r"\D", "", cik)
        if not digits:
            raise ValueError(f"Invalid CIK: {cik}")
        return digits.zfill(10)

    @staticmethod
    def _bytes_to_text(raw: bytes) -> str:
        for encoding in ("utf-8", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")

    @staticmethod
    def _infer_format(primary_document: str) -> str:
        lower = primary_document.lower()
        if lower.endswith(".htm") or lower.endswith(".html"):
            return "html"
        if lower.endswith(".txt"):
            return "text"
        if lower.endswith(".pdf"):
            return "pdf"
        return "unknown"


@lru_cache(maxsize=1)
def _ticker_cik_map_cached(user_agent: str) -> dict[str, str]:
    """Cache ticker→CIK mapping for the process lifetime."""
    logger.info("Loading SEC company ticker map")
    client = HttpClient()
    # Ensure the cached map uses the configured User-Agent.
    client.session.headers["User-Agent"] = user_agent
    payload = client.get(TICKERS_URL, expect_json=True).json()
    mapping: dict[str, str] = {}
    for row in payload.values():
        ticker = str(row.get("ticker", "")).upper()
        cik = str(row.get("cik_str", "")).zfill(10)
        if ticker and cik:
            mapping[ticker] = cik
    logger.info("Loaded %s SEC tickers", len(mapping))
    return mapping


def _load_ticker_cik_map(client: HttpClient) -> dict[str, str]:
    user_agent = client.session.headers.get("User-Agent", "PASI")
    if not isinstance(user_agent, str):
        user_agent = str(user_agent)
    return _ticker_cik_map_cached(user_agent)
