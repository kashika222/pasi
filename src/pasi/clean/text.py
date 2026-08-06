"""Deterministic text cleaning helpers for filings and HTML snapshots."""

from __future__ import annotations

import re
from html.parser import HTMLParser


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = 0
        self._suppress = {"script", "style", "noscript", "svg"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._suppress:
            self._skip += 1
            return
        if self._skip:
            return
        if tag in {"p", "br", "div", "tr", "li", "h1", "h2", "h3", "h4", "td", "th"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._suppress and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = data.strip()
        if text:
            self._chunks.append(text + " ")

    @property
    def text(self) -> str:
        joined = "".join(self._chunks)
        joined = re.sub(r"[ \t]+", " ", joined)
        joined = re.sub(r"\n{3,}", "\n\n", joined)
        return joined.strip()


def html_to_text(html: str) -> str:
    """Extract visible text from HTML; fall back to tag stripping."""
    parser = _VisibleTextParser()
    try:
        parser.feed(html)
        text = parser.text
        if len(text) > 500:
            return text
    except Exception:  # noqa: BLE001
        pass
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_narrative_window(text: str, *, max_chars: int) -> str:
    """Prefer MD&A / business narrative over XBRL header noise.

    Strategy:
    1. Locate common 10-K section anchors (Item 1, Item 7, etc.).
    2. Otherwise score sliding windows by analytics/AI keyword density.
    3. Return up to ``max_chars`` characters from the best region.
    """
    if max_chars <= 0 or len(text) <= max_chars:
        return text

    anchors = [
        r"item\s*7[\.\s:\-].{0,80}management.?s discussion",
        r"management.?s discussion and analysis",
        r"item\s*1[\.\s:\-].{0,40}business",
        r"risk factors",
        r"artificial intelligence",
        r"machine learning",
        r"data analytics",
        r"digital transformation",
    ]
    lower = text.lower()
    start = None
    for pattern in anchors:
        match = re.search(pattern, lower, flags=re.I)
        if match:
            start = match.start()
            break

    if start is None:
        start = _best_keyword_window_start(lower, window=max_chars)
        pad = 0
    else:
        # Small lookback only when preceding text does not look like XBRL/XML noise.
        prelude = lower[max(0, start - 500) : start]
        pad = 0 if ("xmlns" in prelude or "xbrl" in prelude) else 500

    start = max(0, start - pad)
    end = min(len(text), start + max_chars)
    chunk = text[start:end].strip()
    if len(chunk) < max_chars // 5:
        # Degenerate case — fall back to head after skipping likely XBRL prefix.
        soft = min(len(text), max(0, text.find("Item")) if "Item" in text else 0)
        chunk = text[soft : soft + max_chars].strip()
    return chunk


def _best_keyword_window_start(lower_text: str, *, window: int) -> int:
    terms = [
        "analytics",
        "artificial intelligence",
        "machine learning",
        "data-driven",
        "digital transformation",
        "cloud",
        "algorithm",
        "personalization",
        "automation",
        "data science",
    ]
    step = max(1000, window // 4)
    best_start = 0
    best_score = -1
    for start in range(0, max(1, len(lower_text) - window), step):
        chunk = lower_text[start : start + window]
        score = sum(chunk.count(term) for term in terms)
        # Penalize XBRL-heavy regions.
        score -= chunk.count("xbrl") * 2
        score -= chunk.count("xmlns") * 2
        if score > best_score:
            best_score = score
            best_start = start
    return best_start


def prepare_filing_text(raw: str, *, max_chars: int) -> tuple[str, dict]:
    """Clean HTML if needed and select a narrative window for LLM analysis."""
    meta: dict = {
        "original_char_count": len(raw),
        "was_html": False,
        "truncated": False,
        "max_chars": max_chars,
    }
    text = raw.strip()
    if not text:
        meta["sent_char_count"] = 0
        return "", meta

    if "<html" in text.lower() or "<?xml" in text[:200].lower() or "xmlns:" in text[:2000]:
        text = html_to_text(text)
        meta["was_html"] = True
        meta["text_char_count_after_html"] = len(text)

    selected = extract_narrative_window(text, max_chars=max_chars).strip()
    meta["truncated"] = len(selected) < len(text)
    meta["sent_char_count"] = len(selected)
    return selected, meta
