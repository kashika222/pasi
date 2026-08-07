"""Shared Streamlit UI helpers for the PASI research platform.

Visual language follows the Stitch Executive Insight System (modern corporate).
Colors existing scores/confidence only — never invents new KPIs or metrics.
"""

from __future__ import annotations

import html
from typing import Any, Literal

import pandas as pd
import streamlit as st

from pasi.store import clear_repository_cache, ensure_store, get_repository, rebuild_store
from pasi.viz import COLORS

Tone = Literal["leading", "baseline", "lagging", "neutral", "indigo"]

CUSTOM_CSS = f"""
<style>
    .block-container {{
        padding-top: 1.75rem;
        padding-bottom: 3.5rem;
        max-width: 1280px;
    }}

    /* Dark midnight sidebar */
    [data-testid="stSidebar"] {{
        background: {COLORS['navy']} !important;
        border-right: 1px solid #334155;
    }}
    [data-testid="stSidebar"] * {{
        color: #F8FAFC !important;
    }}
    [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small {{
        color: {COLORS['steel']} !important;
    }}
    [data-testid="stSidebarNav"] a {{
        border-radius: 0.75rem !important;
        margin: 0.15rem 0.35rem !important;
        padding-left: 0.75rem !important;
    }}
    [data-testid="stSidebarNav"] a[aria-current="page"] {{
        background: {COLORS['indigo']} !important;
        color: #FFFFFF !important;
    }}
    [data-testid="stSidebarNav"] a:hover {{
        background: rgba(99, 102, 241, 0.25) !important;
    }}
    [data-testid="stSidebar"] .stButton > button {{
        background: {COLORS['indigo']} !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 0.5rem !important;
        font-weight: 600;
    }}
    [data-testid="stSidebar"] code {{
        background: rgba(255,255,255,0.08) !important;
        color: {COLORS['accent_soft']} !important;
    }}

    .pasi-brand {{
        font-size: 0.7rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {COLORS['steel']} !important;
        font-weight: 600;
        margin-bottom: 0.2rem;
    }}
    .pasi-brand-title {{
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 1.35rem;
        color: #FFFFFF !important;
        font-weight: 700;
        margin: 0 0 1.1rem 0;
        line-height: 1.25;
    }}
    .pasi-kicker {{
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-size: 0.72rem;
        color: {COLORS['steel']};
        font-weight: 600;
        margin-bottom: 0.45rem;
    }}
    .pasi-tag {{
        display: inline-block;
        background: #EEF2FF;
        color: {COLORS['indigo_deep']};
        border-radius: 999px;
        padding: 0.28rem 0.75rem;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 0.65rem;
    }}
    .pasi-lede {{
        color: {COLORS['slate']};
        font-size: 1.02rem;
        line-height: 1.6;
        margin: 0.25rem 0 1.25rem 0;
    }}
    .pasi-muted {{
        color: {COLORS['slate']};
        font-size: 0.96rem;
        line-height: 1.6;
    }}
    .pasi-card {{
        border: 1px solid {COLORS['mist']};
        background: #FFFFFF;
        padding: 1.25rem 1.35rem;
        border-radius: 1rem;
        margin-bottom: 0.9rem;
        box-shadow: 0 4px 20px rgba(30, 41, 59, 0.04);
    }}
    .pasi-card-soft {{
        border: 1px solid {COLORS['mist']};
        background: {COLORS['paper']};
        padding: 1.1rem 1.2rem;
        border-radius: 1rem;
        margin-bottom: 0.75rem;
    }}
    .pasi-hero {{
        border: 1px solid {COLORS['mist']};
        background: #FFFFFF;
        padding: 1.5rem 1.6rem;
        border-radius: 1rem;
        box-shadow: 0 4px 20px rgba(30, 41, 59, 0.05);
        margin-bottom: 1rem;
    }}
    .pasi-quote {{
        border-left: 4px solid {COLORS['indigo']};
        padding: 0.7rem 0.9rem;
        margin: 0.55rem 0;
        color: {COLORS['slate']};
        font-style: italic;
        background: {COLORS['paper']};
        border-radius: 0 0.75rem 0.75rem 0;
    }}
    .pasi-chain-step {{
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: {COLORS['steel']};
        font-weight: 600;
        margin-top: 0.35rem;
        margin-bottom: 0.35rem;
    }}
    .pasi-divider {{
        border: none;
        border-top: 1px solid {COLORS['mist']};
        margin: 1.35rem 0;
    }}
    .pasi-ai-box {{
        border: 1px solid {COLORS['mist']};
        background: linear-gradient(135deg, {COLORS['navy']} 0%, #0F172A 100%);
        color: #F8FAFC;
        padding: 1.25rem 1.4rem;
        border-radius: 1rem;
        margin: 0.75rem 0 1rem 0;
        box-shadow: 0 8px 24px rgba(30, 41, 59, 0.18);
    }}
    .pasi-ai-box .pasi-muted {{
        color: #CBD5E1 !important;
    }}
    .pasi-ai-label {{
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: {COLORS['accent_soft']};
        font-weight: 700;
        margin-bottom: 0.5rem;
    }}
    .pasi-pill {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 3.4rem;
        padding: 0.35rem 0.7rem;
        border-radius: 999px;
        font-weight: 600;
        font-variant-numeric: tabular-nums;
        font-size: 0.88rem;
        line-height: 1.2;
    }}
    .pasi-pill-leading {{
        background: {COLORS['success_bg']};
        color: {COLORS['success_text']};
    }}
    .pasi-pill-lagging {{
        background: {COLORS['danger_bg']};
        color: {COLORS['danger_text']};
    }}
    .pasi-pill-baseline {{
        background: {COLORS['neutral_bg']};
        color: {COLORS['neutral_text']};
    }}
    .pasi-pill-indigo {{
        background: #EEF2FF;
        color: {COLORS['indigo_deep']};
    }}
    .pasi-pill-neutral {{
        background: {COLORS['neutral_bg']};
        color: {COLORS['steel']};
    }}
    .pasi-stat {{
        background: {COLORS['paper']};
        border: 1px solid {COLORS['mist']};
        border-radius: 0.85rem;
        padding: 0.95rem 1rem;
        margin-bottom: 0.55rem;
    }}
    .pasi-stat-value {{
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 1.65rem;
        font-weight: 700;
        color: {COLORS['navy']};
        line-height: 1.15;
    }}
    .pasi-stat-label {{
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: {COLORS['steel']};
        font-weight: 600;
        margin-top: 0.25rem;
    }}
    .pasi-progress {{
        height: 8px;
        background: {COLORS['mist']};
        border-radius: 999px;
        overflow: hidden;
        margin: 0.35rem 0 0.15rem 0;
    }}
    .pasi-progress > span {{
        display: block;
        height: 100%;
        border-radius: 999px;
    }}
    .pasi-matrix {{
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        background: #FFFFFF;
        border: 1px solid {COLORS['mist']};
        border-radius: 1rem;
        overflow: hidden;
    }}
    .pasi-matrix th {{
        background: #F1F5F9;
        color: {COLORS['steel']};
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
        padding: 0.85rem 0.75rem;
        text-align: left;
        border-bottom: 1px solid {COLORS['mist']};
    }}
    .pasi-matrix td {{
        padding: 0.7rem 0.75rem;
        border-bottom: 1px solid {COLORS['mist']};
        vertical-align: middle;
    }}
    .pasi-matrix tr:last-child td {{
        border-bottom: none;
    }}
    .pasi-legend {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.65rem;
        margin: 0.35rem 0 0.9rem 0;
        font-size: 0.8rem;
        color: {COLORS['slate']};
    }}
    .pasi-evidence-card {{
        border: 1px solid {COLORS['mist']};
        background: #FFFFFF;
        border-radius: 1rem;
        padding: 1.15rem 1.25rem;
        margin-bottom: 0.9rem;
        box-shadow: 0 4px 20px rgba(30, 41, 59, 0.04);
    }}
    .pasi-source-chip {{
        display: inline-block;
        background: {COLORS['neutral_bg']};
        color: {COLORS['slate']};
        border-radius: 999px;
        padding: 0.2rem 0.65rem;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 0.55rem;
    }}
    div[data-testid="stMetric"] {{
        background: #FFFFFF;
        border: 1px solid {COLORS['mist']};
        border-radius: 0.85rem;
        padding: 0.85rem 1rem;
        box-shadow: 0 2px 12px rgba(30, 41, 59, 0.03);
    }}
    div[data-testid="stMetricValue"] {{
        font-family: 'Playfair Display', Georgia, serif;
        color: {COLORS['navy']};
    }}
    div[data-testid="stMetricLabel"] {{
        color: {COLORS['steel']};
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-size: 0.75rem !important;
    }}
    div[data-testid="stExpander"] {{
        border: 1px solid {COLORS['mist']};
        border-radius: 1rem !important;
        background: #FFFFFF;
        box-shadow: 0 2px 12px rgba(30, 41, 59, 0.03);
    }}
    .stDownloadButton > button,
    .stButton > button {{
        border-radius: 0.5rem !important;
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
    st.markdown(f"<div class='pasi-tag'>{html.escape(kicker)}</div>", unsafe_allow_html=True)
    st.title(title)
    if subtitle:
        st.markdown(f"<p class='pasi-lede'>{html.escape(subtitle)}</p>", unsafe_allow_html=True)


def section_label(text: str) -> None:
    st.markdown(f"<div class='pasi-kicker'>{html.escape(text)}</div>", unsafe_allow_html=True)


def missing_data_notice(message: str) -> None:
    st.info(message)


def tone_for_score(score: float | None) -> Tone:
    """Map existing 0–2 dimension scores to leading / baseline / lagging."""
    if score is None:
        return "neutral"
    if score >= 1.5:
        return "leading"
    if score >= 0.5:
        return "baseline"
    return "lagging"


def tone_for_confidence(confidence: float | None) -> Tone:
    """Map existing 0–1 confidence to green / indigo / red."""
    if confidence is None:
        return "neutral"
    if confidence >= 0.75:
        return "leading"
    if confidence >= 0.45:
        return "indigo"
    return "lagging"


def tone_for_assessment(assessment: str | None) -> Tone:
    text = (assessment or "").lower()
    if "strong" in text:
        return "leading"
    if "partial" in text:
        return "indigo"
    if "weak" in text or "absent" in text:
        return "lagging"
    return "neutral"


def render_pill(text: str, tone: Tone = "baseline") -> None:
    st.markdown(
        f"<span class='pasi-pill pasi-pill-{tone}'>{html.escape(str(text))}</span>",
        unsafe_allow_html=True,
    )


def render_score_pill(score: float | None) -> None:
    if score is None:
        render_pill("n/a", "neutral")
        return
    render_pill(f"{score:.2f}", tone_for_score(score))


def render_confidence_pill(confidence: float | None) -> None:
    if confidence is None:
        render_pill("n/a", "neutral")
        return
    render_pill(f"{confidence:.2f}", tone_for_confidence(confidence))


def render_metric_tile(label: str, value: str, *, tone: Tone | None = None) -> None:
    value_html = html.escape(str(value))
    if tone:
        value_html = f"<span class='pasi-pill pasi-pill-{tone}'>{value_html}</span>"
    else:
        value_html = f"<div class='pasi-stat-value'>{value_html}</div>"
    st.markdown(
        f"""
<div class="pasi-stat">
  {value_html}
  <div class="pasi-stat-label">{html.escape(label)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_confidence_bar(confidence: float | None, label: str = "Confidence") -> None:
    if confidence is None:
        render_pill("n/a", "neutral")
        return
    tone = tone_for_confidence(confidence)
    color = {
        "leading": COLORS["success"],
        "indigo": COLORS["indigo"],
        "lagging": COLORS["danger"],
        "baseline": COLORS["steel"],
        "neutral": COLORS["steel"],
    }[tone]
    pct = max(0.0, min(1.0, float(confidence))) * 100
    st.markdown(
        f"""
<div class="pasi-kicker">{html.escape(label)}</div>
<div class="pasi-progress"><span style="width:{pct:.1f}%;background:{color};"></span></div>
<div style="display:flex;justify-content:space-between;align-items:center;">
  <span class="pasi-muted">{pct:.0f}%</span>
  <span class="pasi-pill pasi-pill-{tone}">{float(confidence):.2f}</span>
</div>
""",
        unsafe_allow_html=True,
    )


def render_score_legend() -> None:
    st.markdown(
        """
<div class="pasi-legend">
  <span class="pasi-pill pasi-pill-leading">Strong (≥ 1.5)</span>
  <span class="pasi-pill pasi-pill-baseline">Partial (0.5–1.5)</span>
  <span class="pasi-pill pasi-pill-lagging">Weak (&lt; 0.5)</span>
</div>
""",
        unsafe_allow_html=True,
    )


def render_score_matrix(matrix: pd.DataFrame) -> None:
    """Color existing dimension scores in a Stitch-style pill matrix (no new metrics)."""
    if matrix.empty:
        st.caption("No matrix data available.")
        return
    rounded = matrix.round(2)
    header = "".join(f"<th>{html.escape(str(col))}</th>" for col in rounded.columns)
    rows: list[str] = []
    for idx, row in rounded.iterrows():
        cells = [f"<td><strong>{html.escape(str(idx))}</strong></td>"]
        for value in row.tolist():
            if pd.isna(value):
                cells.append("<td><span class='pasi-pill pasi-pill-neutral'>n/a</span></td>")
                continue
            score = float(value)
            tone = tone_for_score(score)
            cells.append(
                f"<td><span class='pasi-pill pasi-pill-{tone}'>{score:.2f}</span></td>"
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    table = (
        "<table class='pasi-matrix'><thead><tr><th>Company</th>"
        + header
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )
    st.markdown(table, unsafe_allow_html=True)


def render_evidence_quotes(quotes: list[str]) -> None:
    if not quotes:
        st.caption("No evidence quotes in processed outputs for this category.")
        return
    for quote in quotes:
        st.markdown(
            f"<div class='pasi-quote'>{html.escape(quote)}</div>",
            unsafe_allow_html=True,
        )


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


def render_ai_overview(text: str) -> None:
    safe = html.escape(text).replace("\n", "<br/>")
    st.markdown(
        f"""
<div class="pasi-ai-box">
  <div class="pasi-ai-label">AI synthesized overview</div>
  <div class="pasi-muted">{safe}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_evidence_card(item: dict[str, Any], *, dimension_label: str) -> None:
    """Modern evidence card using existing excerpt / interpretation / score / confidence."""
    excerpt = html.escape(str(item.get("excerpt") or ""))
    interpretation = html.escape(str(item.get("interpretation") or "No rationale stored."))
    source = html.escape(str(item.get("source_type") or "source"))
    company = html.escape(str(item.get("company_id") or ""))
    score = item.get("indicator_score")
    confidence = item.get("confidence")
    score_tone = tone_for_score(float(score) if score is not None else None)
    conf_tone = tone_for_confidence(float(confidence) if confidence is not None else None)
    score_txt = "n/a" if score is None else f"{float(score):.2f}"
    conf_txt = "n/a" if confidence is None else f"{float(confidence):.2f}"
    conf_pct = 0.0 if confidence is None else max(0.0, min(1.0, float(confidence))) * 100
    bar_color = {
        "leading": COLORS["success"],
        "indigo": COLORS["indigo"],
        "lagging": COLORS["danger"],
        "baseline": COLORS["steel"],
        "neutral": COLORS["steel"],
    }[conf_tone]

    provenance = item.get("provenance_url") or item.get("document_path") or ""
    provenance_html = (
        f"<div class='pasi-muted' style='margin-top:0.55rem;font-size:0.82rem;'>"
        f"{html.escape(str(provenance))}</div>"
        if provenance
        else ""
    )

    st.markdown(
        f"""
<div class="pasi-evidence-card">
  <span class="pasi-source-chip">{company} · {source}</span>
  <div style="display:grid;grid-template-columns:1.2fr 1fr;gap:1.25rem;">
    <div>
      <div class="pasi-chain-step">Original excerpt</div>
      <div class="pasi-quote">{excerpt}</div>
      {provenance_html}
    </div>
    <div>
      <div class="pasi-chain-step">Interpretation</div>
      <div class="pasi-card-soft pasi-muted">{interpretation}</div>
      <div class="pasi-chain-step">Indicator mapping</div>
      <div style="display:flex;justify-content:space-between;align-items:center;gap:0.5rem;">
        <strong>{html.escape(dimension_label)}</strong>
        <span class="pasi-pill pasi-pill-{score_tone}">score {score_txt}</span>
      </div>
      <div class="pasi-progress"><span style="width:{conf_pct:.1f}%;background:{bar_color};"></span></div>
      <div style="display:flex;justify-content:flex-end;">
        <span class="pasi-pill pasi-pill-{conf_tone}">{conf_txt} confidence</span>
      </div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def sidebar_controls() -> None:
    """Workspace controls; ensure analytical store exists on first load."""
    ensure_store()

    st.sidebar.markdown(
        "<div class='pasi-brand'>Internal analytics</div>"
        "<div class='pasi-brand-title'>Executive Desk</div>",
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("##### Workspace")
    st.sidebar.caption("Rebuild indexes from `data/raw`, catalog, and `data/processed/ai`.")
    if st.sidebar.button(
        "Refresh analytical store",
        type="primary",
        width="stretch",
        icon=":material/refresh:",
    ):
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
