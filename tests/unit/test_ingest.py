"""Unit tests for ingest collectors (no live network)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pasi.ingest.careers import CareersPageCollector
from pasi.ingest.earnings import EarningsTranscriptCollector
from pasi.ingest.employee_reviews import EmployeeReviewDatasetLoader
from pasi.ingest.schema import CollectionStatus, SourceType
from pasi.ingest.sec_10k import SecTenKCollector


def test_earnings_from_local_file(tmp_path: Path) -> None:
    path = tmp_path / "call.txt"
    path.write_text("Welcome to the Q1 earnings call. Analytics investment continued.", encoding="utf-8")

    doc = EarningsTranscriptCollector().collect(
        company_id="netflix",
        company_name="Netflix",
        file_path=path,
        fiscal_period="2024-Q1",
    )
    assert doc.source_type is SourceType.EARNINGS_CALL
    assert doc.status is CollectionStatus.SUCCESS
    assert "earnings call" in doc.content["text"].lower()
    assert doc.provenance.content_sha256
    payload = doc.to_json_dict()
    assert payload["schema_version"] == "1.0"
    assert payload["content"]["char_count"] > 0


def test_earnings_requires_exactly_one_source() -> None:
    doc = EarningsTranscriptCollector().collect(company_id="netflix")
    assert doc.status is CollectionStatus.ERROR


def test_employee_reviews_csv_filter(tmp_path: Path) -> None:
    path = tmp_path / "reviews.csv"
    path.write_text(
        "company,review_text,rating\n"
        "Netflix,Great data culture,5\n"
        "Uber,Ops focused,3\n"
        "Netflix,Strong analytics tooling,4\n",
        encoding="utf-8",
    )
    doc = EmployeeReviewDatasetLoader().collect(
        company_id="netflix",
        company_name="Netflix",
        dataset_path=path,
        company_filter="Netflix",
        company_column="company",
    )
    assert doc.status is CollectionStatus.SUCCESS
    assert doc.content["record_count"] == 2
    assert all(r["company"] == "Netflix" for r in doc.content["records"])


def test_employee_reviews_missing_file(tmp_path: Path) -> None:
    doc = EmployeeReviewDatasetLoader().collect(
        company_id="netflix",
        dataset_path=tmp_path / "missing.csv",
    )
    assert doc.status is CollectionStatus.ERROR


def test_careers_from_local_html(tmp_path: Path) -> None:
    path = tmp_path / "careers.html"
    path.write_text(
        """
        <html><head><script>ignore()</script></head>
        <body>
          <h1>Careers</h1>
          <p>Join our Data Science team</p>
          <a href="/jobs/data-scientist">Data Scientist</a>
          <a href="/about">About</a>
        </body></html>
        """,
        encoding="utf-8",
    )
    doc = CareersPageCollector().collect(
        company_id="snowflake",
        company_name="Snowflake",
        file_path=path,
        careers_url="https://careers.example.com/",
    )
    assert doc.status is CollectionStatus.SUCCESS
    assert "Data Science" in doc.content["text"]
    assert doc.metadata["job_like_link_count"] >= 1
    assert doc.content["html"]


def test_careers_requires_opt_in_fetch() -> None:
    doc = CareersPageCollector().collect(
        company_id="snowflake",
        careers_url="https://careers.example.com/",
        allow_fetch=False,
    )
    assert doc.status is CollectionStatus.ERROR
    assert "allow_fetch" in doc.errors[0]


def test_sec_10k_mocked_download() -> None:
    submissions = {
        "filings": {
            "recent": {
                "form": ["10-Q", "10-K", "8-K"],
                "accessionNumber": ["0001", "0002-11-22", "0003"],
                "filingDate": ["2024-06-01", "2024-03-15", "2024-01-01"],
                "reportDate": ["2024-05-01", "2023-12-31", "2024-01-01"],
                "primaryDocument": ["a.htm", "b.htm", "c.htm"],
            }
        }
    }
    html = b"<html><body>Item 7 Management discussion analytics</body></html>"

    client = MagicMock()

    def fake_get(url, **kwargs):  # noqa: ANN003
        response = MagicMock()
        response.status_code = 200
        if "company_tickers" in url:
            response.json.return_value = {
                "0": {"ticker": "NFLX", "cik_str": 1065280},
            }
            response.content = b"{}"
        elif "submissions" in url:
            response.json.return_value = submissions
            response.content = b"{}"
        else:
            response.content = html
            response.json.side_effect = ValueError("not json")
        return response

    client.get.side_effect = fake_get
    client.session.headers = {"User-Agent": "PASI test@example.com"}

    with patch("pasi.ingest.sec_10k._ticker_cik_map_cached", return_value={"NFLX": "0001065280"}):
        collector = SecTenKCollector(client=client)
        doc = collector.collect(
            company_id="netflix",
            company_name="Netflix",
            ticker="NFLX",
        )

    assert doc.status is CollectionStatus.SUCCESS
    assert doc.metadata["form"] == "10-K"
    assert "analytics" in doc.content["text"].lower()
    assert doc.provenance.url.endswith("b.htm")


def test_sec_10k_missing_ticker() -> None:
    doc = SecTenKCollector().collect(company_id="databricks", company_name="Databricks")
    assert doc.status is CollectionStatus.ERROR


def test_archive_document(tmp_path: Path) -> None:
    from pasi.config.settings import Settings, get_settings
    from pasi.ingest.archive import archive_document
    from pasi.ingest.schema import CollectedDocument, Provenance

    get_settings.cache_clear()
    settings = Settings(data_dir=tmp_path / "data")

    doc = CollectedDocument(
        source_type=SourceType.EARNINGS_CALL,
        company_id="netflix",
        status=CollectionStatus.SUCCESS,
        provenance=Provenance(method="local_file", license_note="test"),
        content={"text": "hello"},
    )
    path = archive_document(doc, settings=settings, raw_bytes=b"hello", raw_suffix=".txt")
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["company_id"] == "netflix"
    assert loaded["source_type"] == "earnings_call"
    assert loaded["provenance"]["local_path"]
    get_settings.cache_clear()
