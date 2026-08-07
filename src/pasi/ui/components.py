"""Shared Streamlit UI helpers for the PASI research platform.

Visual language follows the Stitch Executive Insight System (consulting editorial).
Does not invent scores — only presents pipeline outputs.
"""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from pasi.store import clear_repository_cache, ensure_store, get_repository, rebuild_store
from pasi.viz import COLORS

# Layout accents config.toml cannot express (evidence cards, kickers, quote rules).
CUSTOM_CSS = f"""
<style>
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 3.5rem;
        max-width: 1140px;
    }}

    [data-testid="stSidebar"] {{
        border-right: 1px solid {COLORS['mist']};
    }}
    [data-testid="stSidebarNav"] a[aria-current="page"] {{
        background: #CEE2F3 !important;
        border-left: 3px solid {COLORS['navy']};
    }}
    [data-testid="stSidebarNav"] a:hover {{
        background: #EEEEEE !important;
    }}

    .pasi-brand {{
        font-size: 0.72rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {COLORS['steel']};
        font-weight: 600;
        margin-bottom: 0.15rem;
    }}
    .pasi-brand-title {{
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 1.15rem;
        color: {COLORS['navy']};
        font-weight: 700;
        margin: 0 0 1rem 0;
        line-height: 1.3;
    }}
    .pasi-kicker {{
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.72rem;
        color: {COLORS['steel']};
        font-weight: 600;
        margin-bottom: 0.45rem;
    }}
    .pasi-lede {{
        color: {COLORS['slate']};
        font-size: 1.05rem;
        line-height: 1.65;
        font-style: italic;
        margin: 0.35rem 0 1.4rem 0;
    }}
    .pasi-muted {{
        color: {COLORS['slate']};
        font-size: 0.98rem;
        line-height: 1.6;
    }}
    .pasi-card {{
        border: 1px solid {COLORS['mist']};
        background: #FFFFFF;
        padding: 1.15rem 1.25rem;
        border-radius: 0;
        margin-bottom: 0.85rem;
    }}
    .pasi-card-soft {{
        border: 1px solid {COLORS['mist']};
        background: {COLORS['paper']};
        padding: 1.15rem 1.25rem;
        border-radius: 0;
        margin-bottom: 0.85rem;
    }}
    .pasi-quote {{
        border-left: 3px solid {COLORS['navy']};
        padding: 0.45rem 0 0.45rem 0.95rem;
        margin: 0.55rem 0;
        color: {COLORS['slate']};
        font-style: italic;
        background: {COLORS['paper']};
    }}
    .pasi-chain-step {{
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: {COLORS['steel']};
        font-weight: 600;
        margin-top: 0.75rem;
    }}
    .pasi-divider {{
        border: none;
        border-top: 1px solid {COLORS['mist']};
        margin: 1.5rem 0;
    }}
    .pasi-ai-box {{
        border: 1px solid {COLORS['mist']};
        border-top: 3px solid {COLORS['navy']};
        background: #FFFFFF;
        padding: 1rem 1.15rem;
        margin: 0.75rem 0 1rem 0;
    }}
    .pasi-ai-label {{
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: {COLORS['navy']};
        font-weight: 700;
        margin-bottom: 0.4rem;
    }}
    div[data-testid="stMetric"] {{
        background: #FFFFFF;
        border: 1px solid {COLORS['mist']};
        padding: 0.85rem 1rem;
    }}
    div[data-testid="stMetricValue"] {{
        font-family: 'Playfair Display', Georgia, serif;
        color: {COLORS['navy']};
    }}
    div[data-testid="stMetricLabel"] {{
        color: {COLORS['slate']};
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-size: 0.78rem !important;
    }}
    div[data-testid="stExpander"] {{
        border: 1px solid {COLORS['mist']};
        border-radius: 0 !important;
        background: #FFFFFF;
    }}
    .stDownloadButton > button,
    .stButton > button {{
        border-radius: 0 !important;
    }}
</style>
"""


def inject_theme() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def page_header(
    title: str,
    subtitle: str | None = None,
    kicker: str = "PASI Research Platform",
) -> None:
    st.markdown(f"<div class='pasi-kicker'>{kicker}</div>", unsafe_allow_html=True)
    st.title(title)
    if subtitle:
        st.markdown(f"<p class='pasi-lede'>{subtitle}</p>", unsafe_allow_html=True)


def section_label(text: str) -> None:
    st.markdown(f"<div class='pasi-kicker'>{text}</div>", unsafe_allow_html=True)


def missing_data_notice(message: str) -> None:
    st.info(message)


def render_evidence_quotes(quotes: list[str]) -> None:
    if not quotes:
        st.caption("No evidence quotes in processed outputs for this category.")
        return
    for quote in quotes:
        st.markdown(f"<div class='pasi-quote'>{quote}</div>", unsafe_allow_html=True)


def render_source_refs(refs: list[dict[str, Any]]) -> None:
    if not refs:
        st.caption("No source documents indexed yet.")
        return
    for ref in refs:
        label = ref.get("source_type") or "source"
        date = ref.get("filing_date") or ""
        url = ref.get("url")
        path = ref.get("path")
        line = f"**{label}**"
        if date:
            line += f" · {date}"
        st.markdown(line)
        if url:
            st.caption(str(url))
        elif path:
            st.caption(str(path))


def render_ai_overview(text: str) -> None:
    safe = html.escape(text).replace("\n", "<br/>")
    st.markdown(
        f"""
<div class="pasi-ai-box">
  <div class="pasi-ai-label">AI synthesized overview</div>
  <div class="pasi-muted">{safe}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def sidebar_controls() -> None:
    """Workspace controls; ensure analytical store exists on first load."""
    ensure_store()

    st.sidebar.markdown(
        "<div class='pasi-brand'>Enterprise analytics</div>"
        "<div class='pasi-brand-title'>Research Console</div>",
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("##### Workspace")
    st.sidebar.caption("Rebuild indexes from `data/raw`, catalog, and `data/processed/ai`.")
    if st.sidebar.button(
        "Refresh analytical store",
        type="primary",
        width="stretch",
        icon=":material/refresh:",
    ):
        counts = rebuild_store()
        clear_repository_cache()
        st.sidebar.success(
            f"Indexed {counts.get('companies', 0)} companies, "
            f"{counts.get('documents', 0)} docs, "
            f"{counts.get('analyses', 0)} analyses."
        )
        st.rerun()

    repo = get_repository()
    meta = repo.meta()
    if meta.get("built_at"):
        st.sidebar.caption(f"Store built: {meta['built_at']}")
    coverage = repo.coverage_summary()
    with_docs = int((coverage["documents"] > 0).sum()) if not coverage.empty else 0
    with_ai = int((coverage["analyses"] > 0).sum()) if not coverage.empty else 0
    st.sidebar.markdown(
        f"Coverage: **{with_docs}** companies with documents · "
        f"**{with_ai}** with AI analyses"
    )
