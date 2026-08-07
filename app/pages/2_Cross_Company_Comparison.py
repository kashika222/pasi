"""Cross-company comparison workspace."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pathsetup  # noqa: F401

import streamlit as st

from pasi.services import comparison_payload, export_dimension_csv
from pasi.store import get_repository
from pasi.ui import inject_theme, missing_data_notice, page_header, section_label, sidebar_controls
from pasi.viz import distribution, grouped_bar, heatmap, multi_radar

st.set_page_config(page_title="PASI | Comparison", layout="wide")
inject_theme()
sidebar_controls()

page_header(
    "Cross Company Comparison",
    "Compare public analytics-maturity signals across the cohort using only processed scores.",
)

repo = get_repository()
companies = repo.companies()
if companies.empty:
    st.error("No companies configured.")
    st.stop()

name_to_id = dict(zip(companies["name"], companies["company_id"], strict=False))
default = companies["name"].tolist()[:4]

filter_row, export_row = st.columns([1.4, 0.6], gap="large")
with filter_row:
    selected_names = st.multiselect(
        "Companies to compare",
        options=companies["name"].tolist(),
        default=default,
    )
with export_row:
    st.download_button(
        "Download dimension CSV",
        data=export_dimension_csv(repo),
        file_name="pasi_dimension_scores.csv",
        mime="text/csv",
        icon=":material/download:",
        width="stretch",
    )

selected_ids = [name_to_id[n] for n in selected_names]
payload = comparison_payload(repo, selected_ids if selected_ids else None)

if not payload["has_data"]:
    missing_data_notice(
        "No AI dimension scores are indexed yet. Analyze collected documents with "
        "`pasi analyze`, refresh the store, then return here."
    )
    section_label("Collection coverage")
    st.dataframe(repo.coverage_summary(), width="stretch", hide_index=True)
    st.stop()

long_df = payload["long"]
matrix = payload["matrix"]

section_label("Strategic framework alignment")
st.plotly_chart(
    multi_radar(payload["radar"], title="Dimension scores by company"),
    width="stretch",
)

col_a, col_b = st.columns(2, gap="large")
with col_a:
    section_label("Score heatmap")
    st.plotly_chart(
        heatmap(matrix, title="Company × dimension score heatmap"),
        width="stretch",
    )
with col_b:
    section_label("Score distribution")
    st.plotly_chart(
        distribution(long_df, x="score", title="Distribution of dimension scores"),
        width="stretch",
    )

section_label("Grouped comparison")
st.plotly_chart(
    grouped_bar(
        long_df,
        x="dimension_label",
        y="score",
        color="company_name",
        title="Scores by dimension",
    ),
    width="stretch",
)

section_label("Underlying matrix")
st.dataframe(matrix.round(2), width="stretch")
