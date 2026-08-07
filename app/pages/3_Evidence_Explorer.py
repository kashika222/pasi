"""Evidence Explorer — excerpt → interpretation → indicator."""

from __future__ import annotations

import streamlit as st

from pasi.ai.schema import DIMENSION_LABELS, DimensionId
from pasi.services import evidence_trail
from pasi.store import get_repository
from pasi.ui import inject_theme, missing_data_notice, page_header, section_label, sidebar_controls

st.set_page_config(page_title="PASI | Evidence Explorer", layout="wide")
inject_theme()
sidebar_controls()

page_header(
    "Evidence Explorer",
    "Trace every conclusion: original excerpt → AI interpretation → final indicator.",
)

repo = get_repository()
companies = repo.companies()
docs = repo.documents()

company_options = ["All"] + companies["name"].tolist()
source_options = ["All", "ten_k", "earnings_call", "employee_reviews", "careers"]
dimension_options = ["All"] + [d.value for d in DimensionId]

c1, c2, c3 = st.columns(3)
company_name = c1.selectbox("Company", company_options)
source_type = c2.selectbox("Source family", source_options)
dimension_id = c3.selectbox("Dimension", dimension_options)
search = st.text_input("Search excerpts", placeholder="e.g. machine learning, data platform")

name_to_id = dict(zip(companies["name"], companies["company_id"], strict=False))
company_id = None if company_name == "All" else name_to_id.get(company_name)

section_label("Indexed source documents")
doc_view = docs.copy()
if company_id:
    doc_view = doc_view[doc_view["company_id"] == company_id]
if source_type != "All":
    doc_view = doc_view[doc_view["source_type"] == source_type]
if doc_view.empty:
    missing_data_notice("No source documents match the current filters.")
else:
    st.dataframe(
        doc_view[
            [
                "company_id",
                "source_type",
                "status",
                "filing_date",
                "provenance_url",
                "char_count",
            ]
        ],
        width="stretch",
        hide_index=True,
    )

section_label("Evidence chains")
trails = evidence_trail(
    repo,
    company_id=company_id,
    source_type=None if source_type == "All" else source_type,
    dimension_id=None if dimension_id == "All" else dimension_id,
    search=search or None,
)

if not trails:
    missing_data_notice(
        "No evidence items available. Evidence appears after successful AI analysis "
        "outputs are written to `data/processed/ai` and the store is refreshed."
    )
    st.stop()

st.caption(f"Showing {len(trails)} evidence item(s)")
label_lookup = {d.value: label for d, label in DIMENSION_LABELS.items()}
for item in trails:
    dim_label = label_lookup.get(item["dimension_id"], item["dimension_id"])
    header = (
        f"{item['company_id']} · {item['source_type']} · {dim_label} "
        f"(score={item['indicator_score']}, confidence={item['confidence']})"
    )
    with st.expander(header):
        cols = st.columns([1.2, 1, 0.8], gap="medium")
        with cols[0]:
            st.markdown("<div class='pasi-chain-step'>Original excerpt</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='pasi-quote'>{item['excerpt']}</div>", unsafe_allow_html=True)
        with cols[1]:
            st.markdown("<div class='pasi-chain-step'>AI interpretation</div>", unsafe_allow_html=True)
            st.write(item["interpretation"] or "No rationale stored for this item.")
        with cols[2]:
            st.markdown("<div class='pasi-chain-step'>Final indicator</div>", unsafe_allow_html=True)
            st.metric("Score", item["indicator_score"], border=True)
            st.metric("Confidence", item["confidence"], border=True)
            st.caption(f"Dimension: `{item['dimension_id']}`")
        if item.get("provenance_url"):
            st.caption(f"Source: {item['provenance_url']}")
        if item.get("document_path"):
            st.caption(f"Document path: {item['document_path']}")
