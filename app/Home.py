"""PASI Research Platform — Home."""

from __future__ import annotations

import pathsetup  # noqa: F401 — prefer repo src/ on Streamlit Cloud
import streamlit as st

from pasi.store import get_repository
from pasi.ui import inject_theme, page_header, section_label, sidebar_controls

st.set_page_config(
    page_title="PASI | Research Platform",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()
sidebar_controls()

page_header(
    "Public Analytics Signal Index",
    "An AI-assisted research platform for assessing organizational analytics maturity "
    "from publicly observable signals.",
    kicker="Central research inquiry",
)

repo = get_repository()
companies = repo.companies()
coverage = repo.coverage_summary()
docs = repo.documents()
analyses = repo.analyses()
with_ai = int((coverage["analyses"] > 0).sum()) if not coverage.empty else 0

main, aside = st.columns([1.55, 0.85], gap="large")

with main:
    st.markdown(
        """
<div class="pasi-hero pasi-muted">
Can publicly available organizational signals — annual reports, earnings communication,
talent postings, and licensed employee-review datasets — be used to assess an
organization’s analytics maturity in a transparent, evidence-linked way?
</div>
""",
        unsafe_allow_html=True,
    )

    section_label("Cohort overview")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Companies in cohort", len(companies), border=True)
    with c2:
        st.metric("Documents indexed", len(docs), border=True)
    c3, c4 = st.columns(2)
    with c3:
        st.metric("AI analyses indexed", len(analyses), border=True)
    with c4:
        st.metric("Companies with AI output", with_ai, border=True)

    st.markdown('<hr class="pasi-divider" />', unsafe_allow_html=True)

    section_label("Companies analyzed")
    if companies.empty:
        st.warning("No companies found in configuration.")
    else:
        display = companies[
            ["name", "ticker", "segment", "industry", "proxy_label", "document_count", "analysis_count"]
        ].rename(
            columns={
                "name": "Company",
                "ticker": "Ticker",
                "segment": "Segment",
                "industry": "Industry",
                "proxy_label": "Contrast label",
                "document_count": "Documents",
                "analysis_count": "Analyses",
            }
        )
        st.dataframe(display, width="stretch", hide_index=True)

with aside:
    section_label("Primary sources")
    st.markdown(
        """
<div class="pasi-card-soft pasi-muted">
<strong>Annual reports / Form 10-K</strong><br/>
Leadership, strategy, disclosure language
</div>
<div class="pasi-card-soft pasi-muted">
<strong>Earnings call transcripts</strong><br/>
Forward-looking analytics / AI priorities
</div>
<div class="pasi-card-soft pasi-muted">
<strong>Employee review datasets</strong><br/>
Culture and adoption perception (licensed data only)
</div>
<div class="pasi-card-soft pasi-muted">
<strong>Company careers pages</strong><br/>
Talent investment and role-mix signals
</div>
""",
        unsafe_allow_html=True,
    )

    section_label("Methodology summary")
    st.markdown(
        """
<div class="pasi-card pasi-muted">
1. <strong>Collect</strong> public artifacts into standardized JSON with provenance.<br/><br/>
2. <strong>Analyze</strong> clean text with versioned prompts via configured LLM.<br/><br/>
3. <strong>Index</strong> raw + AI outputs into DuckDB for research exploration.<br/><br/>
4. <strong>Explain</strong> every score through evidence chains
(excerpt → interpretation → indicator).
</div>
""",
        unsafe_allow_html=True,
    )
    st.page_link(
        "pages/4_Methodology.py",
        label="Read full methodology",
        icon=":material/arrow_forward:",
    )

st.caption(
    "PASI is an exploratory public-signal index — not a validated measure of internal analytics capability."
)
