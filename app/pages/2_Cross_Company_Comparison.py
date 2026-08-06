"""Cross-company comparison workspace."""

from __future__ import annotations

import streamlit as st

from pasi.services import comparison_payload, export_dimension_csv
from pasi.store import get_repository
from pasi.ui import inject_theme, missing_data_notice, page_header, sidebar_controls
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
selected_names = st.multiselect(
    "Companies to compare",
    options=companies["name"].tolist(),
    default=default,
)
selected_ids = [name_to_id[n] for n in selected_names]

payload = comparison_payload(repo, selected_ids if selected_ids else None)

st.download_button(
    "Download processed dimension dataset (CSV)",
    data=export_dimension_csv(repo),
    file_name="pasi_dimension_scores.csv",
    mime="text/csv",
)

if not payload["has_data"]:
    missing_data_notice(
        "No AI dimension scores are indexed yet. Analyze collected documents with "
        "`pasi analyze`, refresh the store, then return here."
    )
    st.markdown("### Collection coverage")
    st.dataframe(repo.coverage_summary(), use_container_width=True, hide_index=True)
    st.stop()

long_df = payload["long"]
matrix = payload["matrix"]

st.markdown("### Radar comparison")
st.plotly_chart(
    multi_radar(payload["radar"], title="Dimension scores by company"),
    use_container_width=True,
)

col_a, col_b = st.columns(2)
with col_a:
    st.markdown("### Heatmap")
    st.plotly_chart(
        heatmap(matrix, title="Company × dimension score heatmap"),
        use_container_width=True,
    )
with col_b:
    st.markdown("### Score distribution")
    st.plotly_chart(
        distribution(long_df, x="score", title="Distribution of dimension scores"),
        use_container_width=True,
    )

st.markdown("### Grouped comparison")
st.plotly_chart(
    grouped_bar(
        long_df,
        x="dimension_label",
        y="score",
        color="company_name",
        title="Scores by dimension",
    ),
    use_container_width=True,
)

st.markdown("### Underlying matrix")
st.dataframe(matrix.round(2), use_container_width=True)
