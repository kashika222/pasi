"""Company Explorer — single-organization research workspace."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pathsetup  # noqa: F401

import streamlit as st

from pasi.services import company_profile, executive_summary_text
from pasi.store import get_repository
from pasi.ui import (
    inject_theme,
    missing_data_notice,
    page_header,
    render_ai_overview,
    render_confidence_bar,
    render_evidence_quotes,
    render_pill,
    render_score_legend,
    render_score_pill,
    render_source_refs,
    section_label,
    sidebar_controls,
    tone_for_assessment,
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

names = companies["name"].tolist()
id_by_name = dict(zip(companies["name"], companies["company_id"], strict=False))
query = st.text_input(
    "Search companies",
    placeholder="Type a company name…",
    label_visibility="collapsed",
)
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
SEGMENT_LABELS = {
    "digital_product": "Digital product",
    "data_platform": "Data platform",
    "traditional_regulated": "Traditional",
}
segment = company.get("segment") or "—"

header_l, header_r = st.columns([1.4, 0.6], gap="large")
with header_l:
    section_label(f"{selected_name} analysis")
with header_r:
    st.download_button(
        "Download executive brief",
        data=executive_summary_text(profile),
        file_name=f"{company_id}_executive_brief.txt",
        mime="text/plain",
        icon=":material/download:",
        width="stretch",
    )

top1, top2, top3, top4 = st.columns(4)
top1.metric("Segment", SEGMENT_LABELS.get(str(segment), str(segment)), border=True)
top2.metric("Industry", company.get("industry") or "—", border=True)
top3.metric("Documents", int(company.get("document_count") or 0), border=True)
top4.metric("AI analyses", int(company.get("analysis_count") or 0), border=True)

notes = company.get("notes")
if notes:
    st.caption(str(notes))

if not profile["has_documents"]:
    missing_data_notice(
        "No collected documents are indexed for this company yet. "
        "Run `pasi collect`, then refresh the analytical store."
    )

render_ai_overview(executive_summary_text(profile))

left, right = st.columns([1.05, 0.95], gap="large")
with left:
    section_label("Signal profile")
    if profile["radar_scores"]:
        st.plotly_chart(
            radar_chart(profile["radar_scores"], title=f"{selected_name} — AI dimensions"),
            width="stretch",
        )
    else:
        missing_data_notice(
            "No AI dimension scores available. Run `pasi analyze` on collected documents."
        )

with right:
    section_label("Framework categories")
    st.caption(
        "Leadership Commitment · Talent Investment · Strategic Communication · "
        "Employee Perception · Innovation Signals"
    )
    render_score_legend()
    categories = profile["categories"]
    cat_labels = [c["label"] for c in categories]
    choice = st.radio("Category", options=cat_labels, label_visibility="collapsed")
    cat = categories[cat_labels.index(choice)]

    with st.container(border=True):
        st.markdown(f"### {cat['label']}")
        st.markdown(f"<p class='pasi-muted'>{cat['description']}</p>", unsafe_allow_html=True)

        m1, m2, m3 = st.columns(3)
        with m1:
            section_label("Assessment")
            render_pill(cat["assessment"], tone_for_assessment(cat["assessment"]))
        with m2:
            section_label("Score (0–2)")
            render_score_pill(cat["score"])
        with m3:
            render_confidence_bar(cat["confidence"])

        # Compact category score cards for remaining categories (same metrics only)
        section_label("Category snapshot")
        for other in categories:
            cols = st.columns([1.4, 0.7, 0.7])
            cols[0].markdown(f"**{other['label']}**")
            with cols[1]:
                render_score_pill(other["score"])
            with cols[2]:
                render_pill(
                    other["assessment"].split("/")[0].strip()
                    if other["assessment"]
                    else "n/a",
                    tone_for_assessment(other["assessment"]),
                )

        section_label("AI summary")
        st.write(cat["ai_summary"])

        section_label("Supporting evidence")
        render_evidence_quotes(cat["evidence_quotes"])

        section_label("Source references")
        render_source_refs(cat["document_refs"])
        if cat["source_types"]:
            st.caption("Scored from source types: " + ", ".join(cat["source_types"]))
