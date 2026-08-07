"""Evidence Explorer — excerpt → interpretation → indicator."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pathsetup  # noqa: F401

import streamlit as st

from pasi.ai.schema import DIMENSION_LABELS, DimensionId
from pasi.services import evidence_trail
from pasi.store import get_repository
from pasi.ui import (
    inject_theme,
    missing_data_notice,
    page_header,
    render_evidence_card,
    section_label,
    sidebar_controls,
)

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
search = st.text_input(
    "Search excerpts",
    placeholder="Search excerpts, sources, or tags…",
)

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
    render_evidence_card(item, dimension_label=dim_label)
