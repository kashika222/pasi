"""Methodology — transparent research documentation."""

from __future__ import annotations

import streamlit as st

from pasi.store import get_repository
from pasi.ui import inject_theme, page_header, section_label, sidebar_controls

st.set_page_config(page_title="PASI | Methodology", layout="wide")
inject_theme()
sidebar_controls()

page_header(
    "Methodology",
    "How public signals are collected, analyzed, indexed, and explained.",
)

repo = get_repository()
meta = repo.meta()

tab_pipeline, tab_prompts, tab_limits = st.tabs(
    [
        "I. Pipeline overview",
        "II. Prompt architecture",
        "III. System limitations",
    ]
)

with tab_pipeline:
    section_label("Data pipeline")
    st.markdown(
        """
1. **Configure** the cohort in `configs/companies.yaml`.
2. **Collect** public artifacts (`pasi collect`) into standardized JSON under `data/raw/`.
3. **Analyze** clean text with the configured LLM (`pasi analyze`) into structured dimension JSON under `data/processed/ai/`.
4. **Index** artifacts into DuckDB (`pasi refresh-store` or the sidebar refresh control).
5. **Explore** evidence-linked findings in this research platform.
"""
    )

    section_label("AI workflow")
    st.markdown(
        """
- Input: clean document text (or PASI collection JSON `content.text`).
- Model: configured via `PASI_OPENAI_MODEL` / `PASI_GEMINI_MODEL`.
- Output: six dimensions with score (0–2), confidence (0–1), evidence quotes, and rationale.
- Persistence: versioned analysis JSON; no live LLM calls from this UI.
"""
    )

    section_label("Framework mapping in this application")
    st.markdown(
        """
| Explorer category | Backed by AI dimensions / sources |
| --- | --- |
| Leadership Commitment | `leadership_commitment` |
| Talent Investment | `talent_investment` |
| Strategic Communication | `analytics_strategy`, `ai_strategy` |
| Employee Perception | analyses from `employee_reviews` sources |
| Innovation Signals | `innovation`, `digital_transformation` |
"""
    )

with tab_prompts:
    section_label("Prompting strategy")
    st.markdown(
        """
Prompts are stored **outside code** under `prompts/`:

- `document_analysis_system_v1.txt`
- `document_analysis_user_v1.txt`

Placeholders (`{{DOCUMENT_TEXT}}`, etc.) are rendered at runtime. Prompt version IDs are
stored on every analysis record for reproducibility.
"""
    )
    with st.container(border=True):
        st.markdown(
            """
<div class="pasi-muted">
The semantic extraction models use constrained prompting to prioritize factual recall
over linguistic fluency, explicitly minimizing hallucination risk for research claims.
</div>
""",
            unsafe_allow_html=True,
        )

with tab_limits:
    section_label("Limitations")
    st.markdown(
        """
- Public communication ≠ internal capability or ROI.
- Cross-industry comparisons are descriptive; jargon and disclosure norms differ.
- Earnings / 10-K language is investor-relations managed.
- Careers pages and review datasets have coverage and selection bias.
- LLM judgments require human audit for graded research claims.
- Missing processed outputs are shown as unavailable — scores are never invented.
"""
    )

    section_label("Future improvements")
    st.markdown(
        """
- Expand source coverage across the full 10-company cohort.
- Add human-audit agreement metrics to the Evidence Explorer.
- Segment-normalized comparison views.
- Optional LLM-generated narrative briefs with explicit citation constraints.
- PDF company dossier export.
"""
    )

section_label("Store status")
st.json(meta or {"status": "Store metadata unavailable — refresh the analytical store."})
