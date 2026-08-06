"""PASI Research Platform — Home."""

from __future__ import annotations

import streamlit as st

from pasi.store import get_repository
from pasi.ui import inject_theme, page_header, sidebar_controls

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
)

repo = get_repository()
companies = repo.companies()
coverage = repo.coverage_summary()
docs = repo.documents()
analyses = repo.analyses()

st.markdown("### Research question")
st.markdown(
    """
<div class="pasi-card pasi-muted">
Can publicly available organizational signals — annual reports, earnings communication,
talent postings, and licensed employee-review datasets — be used to assess an
organization’s analytics maturity in a transparent, evidence-linked way?
</div>
""",
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Companies in cohort", len(companies))
c2.metric("Documents indexed", len(docs))
c3.metric("AI analyses indexed", len(analyses))
with_ai = int((coverage["analyses"] > 0).sum()) if not coverage.empty else 0
c4.metric("Companies with AI output", with_ai)

st.markdown("### Companies analyzed")
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
    st.dataframe(display, use_container_width=True, hide_index=True)

st.markdown("### Data sources")
st.markdown(
    """
| Source | Role in the study |
| --- | --- |
| Annual reports / Form 10-K | Leadership, strategy, disclosure language |
| Earnings call transcripts | Forward-looking analytics / AI priorities |
| Employee review datasets | Culture and adoption perception (licensed data only) |
| Company careers pages | Talent investment and role-mix signals |
"""
)

st.markdown("### Methodology (summary)")
st.markdown(
    """
1. **Collect** public artifacts into standardized JSON with provenance.  
2. **Analyze** clean text with versioned prompts via OpenAI.  
3. **Index** raw + AI outputs into DuckDB for research exploration.  
4. **Explain** every score through evidence chains (excerpt → interpretation → indicator).

This application never invents scores. Categories without processed AI output are shown as unavailable.
"""
)

st.caption(
    "PASI is an exploratory public-signal index — not a validated measure of internal analytics capability."
)
