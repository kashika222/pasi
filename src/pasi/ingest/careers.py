"""Read company careers pages from a URL or a local HTML snapshot.

Careers sites often prohibit aggressive scraping. This collector:

* fetches only when ``allow_fetch=True`` and a URL is provided
* prefers local HTML snapshots when available
* extracts visible text and anchor links (no authenticated crawling)
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

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
    "Company careers page snapshot for research. Confirm the site terms allow "
    "automated or manual retrieval before fetching; prefer local exports."
)


class _CareersHTMLParser(HTMLParser):
    """Minimal HTML extractor (stdlib only — no BeautifulSoup required)."""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self.links: list[dict[str, str]] = []
        self._skip_depth = 0
        self._suppress = {"script", "style", "noscript"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._suppress:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append({"href": href, "text": ""})
        if tag in {"p", "br", "li", "tr", "h1", "h2", "h3", "h4", "div"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._suppress and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        self._chunks.append(text + " ")
        if self.links and self.links[-1]["text"] == "":
            self.links[-1]["text"] = text[:200]

    @property
    def text(self) -> str:
        joined = "".join(self._chunks)
        return re.sub(r"[ \t]+\n", "\n", re.sub(r"\n{3,}", "\n\n", joined)).strip()


class CareersPageCollector:
    """Collect careers-page HTML/text into the standard JSON envelope."""

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or HttpClient()

    def collect(
        self,
        *,
        company_id: str,
        company_name: str | None = None,
        careers_url: str | None = None,
        file_path: str | Path | None = None,
        allow_fetch: bool = False,
        max_links: int = 100,
    ) -> CollectedDocument:
        """Read careers content from a local snapshot or (opt-in) HTTP GET."""
        if file_path:
            method = "local_html_snapshot"
        elif careers_url and allow_fetch:
            method = "http_get"
        else:
            return error_document(
                source_type=SourceType.CAREERS,
                company_id=company_id,
                company_name=company_name,
                method="careers_read",
                license_note=LICENSE_NOTE,
                message=(
                    "Provide file_path for a local snapshot, or careers_url with "
                    "allow_fetch=True after confirming site terms permit retrieval"
                ),
                url=careers_url,
            )

        try:
            if file_path is not None:
                path = Path(file_path)
                if not path.exists():
                    raise FileNotFoundError(f"Careers snapshot not found: {path}")
                raw = path.read_bytes()
                html = raw.decode("utf-8", errors="replace")
                url = careers_url or path.resolve().as_uri()
                http_status = None
                local_path = str(path)
            else:
                assert careers_url is not None
                logger.info(
                    "Fetching careers page for %s from %s (allow_fetch=True)",
                    company_id,
                    careers_url,
                )
                response = self.client.get(careers_url)
                raw = response.content
                html = raw.decode("utf-8", errors="replace")
                url = careers_url
                http_status = response.status_code
                local_path = None

            parser = _CareersHTMLParser()
            try:
                parser.feed(html)
                text = parser.text
                links = parser.links
            except Exception:  # noqa: BLE001
                logger.warning("HTML parse failed for %s; returning raw text fallback", company_id)
                text = re.sub(r"<[^>]+>", " ", html)
                text = re.sub(r"\s+", " ", text).strip()
                links = []

            # Absolutize links when we know the page URL.
            abs_links: list[dict[str, str]] = []
            for link in links[:max_links]:
                href = link["href"]
                if careers_url:
                    href = urljoin(careers_url, href)
                abs_links.append({"href": href, "text": link.get("text", "")})

            job_like = [
                link
                for link in abs_links
                if re.search(r"job|career|position|opening|role", link["href"], re.I)
                or re.search(r"job|career|engineer|analyst|data", link.get("text", ""), re.I)
            ]

            status = CollectionStatus.SUCCESS if text else CollectionStatus.PARTIAL
            errors: list[str] = []
            if not text:
                errors.append("No visible text extracted from careers HTML")

            return CollectedDocument(
                source_type=SourceType.CAREERS,
                company_id=company_id,
                company_name=company_name,
                status=status,
                provenance=Provenance(
                    method=method,
                    license_note=LICENSE_NOTE,
                    url=url,
                    content_sha256=sha256_bytes(raw),
                    http_status=http_status,
                    local_path=local_path,
                ),
                metadata={
                    "careers_url": careers_url,
                    "allow_fetch": allow_fetch,
                    "link_count": len(abs_links),
                    "job_like_link_count": len(job_like),
                },
                content={
                    "text": text,
                    "html": html,
                    "char_count": len(text),
                    "sha256_text": sha256_text(text),
                    "links": abs_links,
                    "job_like_links": job_like,
                    "format": "html",
                },
                errors=errors,
            )
        except (OSError, HttpError) as exc:
            logger.exception("Careers collection failed for %s", company_id)
            return error_document(
                source_type=SourceType.CAREERS,
                company_id=company_id,
                company_name=company_name,
                method=method,
                license_note=LICENSE_NOTE,
                message=str(exc),
                url=careers_url,
            )
