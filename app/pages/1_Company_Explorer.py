"""Company Explorer — single-organization research workspace."""

from __future__ import annotations

import streamlit as st

from pasi.services import company_profile, executive_summary_text
from pasi.store import get_repository
from pasi.ui import (
    inject_theme,
    missing_data_notice,
    page_header,
    render_evidence_quotes,
    render_source_refs,
    sidebar_controls,
)
from pasi.viz import radar_chart

st.set_page_config(page_title="PASI | Company Explorer", layout="wide")
inject_theme()
sidebar_controls()

page_header(
    "Company Explorer",
    "Inspect maturity-signal categories for one organization, with evidence and source references.",
)

repo = get_repository()
companies = repo.companies()
if companies.empty:
    st.error("No companies configured.")
    st.stop()

# Search / select
names = companies["name"].tolist()
id_by_name = dict(zip(companies["name"], companies["company_id"], strict=False))
query = st.text_input("Search companies", placeholder="Type a company name…")
filtered = [n for n in names if query.lower() in n.lower()] if query else names
if not filtered:
    st.warning("No companies match your search.")
    st.stop()

selected_name = st.selectbox("Company", filtered)
company_id = id_by_name[selected_name]
profile = company_profile(repo, company_id)
if profile.get("error"):
    st.error(profile["error"])
    st.stop()

company = profile["company"]
top1, top2, top3, top4 = st.columns(4)
segment = company.get("segment") or "—"
# Readable labels in metric tiles (avoid truncation + pandas NaN "nan")
SEGMENT_LABELS = {
    "digital_product": "Digital product",
    "data_platform": "Data platform",
    "traditional_regulated": "Traditional / regulated",
}
top1.metric("Segment", SEGMENT_LABELS.get(str(segment), str(segment)))
top2.metric("Industry", company.get("industry") or "—")
top3.metric("Documents", int(company.get("document_count") or 0))
top4.metric("AI analyses", int(company.get("analysis_count") or 0))

notes = company.get("notes")
if notes:
    st.caption(str(notes))

if not profile["has_documents"]:
    missing_data_notice(
        "No collected documents are indexed for this company yet. "
        "Run `pasi collect`, then refresh the analytical store."
    )

left, right = st.columns([1.05, 0.95])
with left:
    st.markdown("### Signal profile")
    if profile["radar_scores"]:
        st.plotly_chart(
            radar_chart(profile["radar_scores"], title=f"{selected_name} — AI dimensions"),
            use_container_width=True,
        )
    else:
        missing_data_notice(
            "No AI dimension scores available. Run `pasi analyze` on collected documents."
        )

with right:
    st.markdown("### Executive brief")
    brief = executive_summary_text(profile)
    st.text_area("Deterministic summary from processed outputs", brief, height=260)
    st.download_button(
        "Download executive brief (.txt)",
        data=brief,
        file_name=f"{company_id}_executive_brief.txt",
        mime="text/plain",
    )

st.markdown("### Framework categories")
st.caption(
    "Leadership Commitment · Talent Investment · Strategic Communication · "
    "Employee Perception · Innovation Signals"
)

for cat in profile["categories"]:
    with st.expander(f"{cat['label']} — {cat['assessment']}", expanded=False):
        st.markdown(f"<p class='pasi-muted'>{cat['description']}</p>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Assessment", cat["assessment"])
        m2.metric(
            "Score (0–2)",
            f"{cat['score']:.2f}" if cat["score"] is not None else "n/a",
        )
        m3.metric(
            "Confidence",
            f"{cat['confidence']:.2f}" if cat["confidence"] is not None else "n/a",
        )

        st.markdown("**AI summary**")
        st.write(cat["ai_summary"])

        st.markdown("**Supporting evidence**")
        render_evidence_quotes(cat["evidence_quotes"])

        st.markdown("**Source references**")
        render_source_refs(cat["document_refs"])
        if cat["source_types"]:
            st.caption("Scored from source types: " + ", ".join(cat["source_types"]))
