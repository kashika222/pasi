"""Shared Streamlit UI helpers for the PASI research platform."""

from __future__ import annotations

from typing import Any

import streamlit as st

from pasi.store import clear_repository_cache, ensure_store, get_repository, rebuild_store
from pasi.viz import COLORS

CUSTOM_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Libre+Baskerville:wght@400;700&display=swap');

    html, body, [class*="css"]  {{
        font-family: 'IBM Plex Sans', Helvetica, Arial, sans-serif;
    }}
    h1, h2, h3 {{
        font-family: 'Libre Baskerville', Georgia, serif !important;
        color: {COLORS['navy']} !important;
        letter-spacing: -0.01em;
    }}
    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }}

    /* Sidebar: navy chrome so nav links stay readable in light and dark themes */
    [data-testid="stSidebar"] {{
        background: {COLORS['navy']} !important;
        border-right: 1px solid rgba(255,255,255,0.08);
    }}
    [data-testid="stSidebar"] * {{
        color: #F4F6F8 !important;
    }}
    [data-testid="stSidebar"] a,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {{
        color: #F4F6F8 !important;
    }}
    [data-testid="stSidebarNav"] a {{
        background: transparent !important;
        opacity: 1 !important;
    }}
    [data-testid="stSidebarNav"] a:hover,
    [data-testid="stSidebarNav"] a[aria-current="page"] {{
        background: rgba(255,255,255,0.10) !important;
    }}
    [data-testid="stSidebar"] .stButton > button {{
        background: #F4F6F8 !important;
        color: {COLORS['navy']} !important;
        border: none !important;
        font-weight: 600;
    }}
    [data-testid="stSidebar"] code {{
        background: rgba(255,255,255,0.12) !important;
        color: #D7ECE3 !important;
    }}

    .pasi-kicker {{
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.72rem;
        color: {COLORS['steel']};
        font-weight: 600;
        margin-bottom: 0.35rem;
    }}
    .pasi-card {{
        border: 1px solid {COLORS['mist']};
        background: white;
        padding: 1rem 1.1rem;
        border-radius: 2px;
        margin-bottom: 0.75rem;
    }}
    .pasi-muted {{
        color: {COLORS['slate']};
        font-size: 0.95rem;
        line-height: 1.55;
    }}
    .pasi-quote {{
        border-left: 3px solid {COLORS['accent']};
        padding: 0.4rem 0 0.4rem 0.9rem;
        margin: 0.5rem 0;
        color: {COLORS['slate']};
        font-style: italic;
    }}
    .pasi-chain-step {{
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: {COLORS['steel']};
        margin-top: 0.6rem;
    }}
    div[data-testid="stMetricValue"] {{
        font-family: 'Libre Baskerville', Georgia, serif;
        color: {COLORS['navy']};
        font-size: 1.35rem !important;
    }}
    div[data-testid="stMetricLabel"] {{
        color: {COLORS['slate']};
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
        st.markdown(f"<p class='pasi-muted'>{subtitle}</p>", unsafe_allow_html=True)


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


def sidebar_controls() -> None:
    """Workspace controls; ensure analytical store exists on first load."""
    # Cloud / fresh clones: rebuild DuckDB from committed analyses + catalog.
    ensure_store()

    st.sidebar.markdown("### Workspace")
    st.sidebar.caption("Rebuild indexes from `data/raw`, catalog, and `data/processed/ai`.")
    if st.sidebar.button("Refresh analytical store", use_container_width=True):
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
