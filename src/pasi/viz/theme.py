"""Professional visualization theme and Plotly chart builders."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Stitch "Executive Insight System" consulting palette.
COLORS = {
    "navy": "#002B49",
    "navy_deep": "#001629",
    "slate": "#4E616F",
    "steel": "#8A9BA8",
    "mist": "#D1D5DB",
    "paper": "#F8F9FA",
    "surface": "#F9F9F9",
    "ink": "#1A1C1C",
    "accent": "#2E5D82",
    "accent_soft": "#7293B6",
    "warn": "#9B2C2C",
    "muted": "#B5C9DA",
}

SCORE_COLORS = {
    0: "#D1D5DB",
    1: "#7293B6",
    2: "#002B49",
}

_PALETTE = [
    COLORS["navy"],
    COLORS["accent"],
    COLORS["slate"],
    COLORS["accent_soft"],
    COLORS["steel"],
    COLORS["muted"],
]


def apply_layout(fig: go.Figure, *, title: str | None = None, height: int = 420) -> go.Figure:
    fig.update_layout(
        title=dict(
            text=title or "",
            font=dict(size=16, color=COLORS["navy"], family="Playfair Display, Georgia, serif"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Source Sans 3, Helvetica, Arial, sans-serif", color=COLORS["slate"], size=12),
        margin=dict(l=40, r=30, t=60 if title else 30, b=40),
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["mist"], zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["mist"], zeroline=False)
    return fig


def radar_chart(
    scores: dict[str, float],
    *,
    title: str | None = None,
    max_score: float = 2.0,
) -> go.Figure:
    """Radar for one company. ``scores`` maps dimension label → value."""
    if not scores:
        fig = go.Figure()
        fig.add_annotation(text="No scored dimensions available", showarrow=False)
        return apply_layout(fig, title=title)

    labels = list(scores.keys())
    values = [float(scores[k]) for k in labels]
    labels_c = labels + [labels[0]]
    values_c = values + [values[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values_c,
            theta=labels_c,
            fill="toself",
            fillcolor="rgba(46, 93, 130, 0.12)",
            line=dict(color=COLORS["accent"], width=2),
            name="Score",
        )
    )
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, max_score], gridcolor=COLORS["mist"]),
            angularaxis=dict(gridcolor=COLORS["mist"]),
        )
    )
    return apply_layout(fig, title=title, height=460)


def multi_radar(
    company_scores: dict[str, dict[str, float]],
    *,
    title: str | None = None,
    max_score: float = 2.0,
) -> go.Figure:
    """Overlay radars for multiple companies (same dimension labels)."""
    fig = go.Figure()
    if not company_scores:
        fig.add_annotation(text="No comparison data available", showarrow=False)
        return apply_layout(fig, title=title)

    labels: list[str] = []
    for scores in company_scores.values():
        for label in scores:
            if label not in labels:
                labels.append(label)

    for idx, (company, scores) in enumerate(company_scores.items()):
        values = [float(scores.get(label, 0)) for label in labels]
        labels_c = labels + ([labels[0]] if labels else [])
        values_c = values + ([values[0]] if values else [])
        color = _PALETTE[idx % len(_PALETTE)]
        fig.add_trace(
            go.Scatterpolar(
                r=values_c,
                theta=labels_c,
                name=company,
                line=dict(color=color, width=2, dash="solid" if idx == 0 else "dot"),
                fill="toself",
                fillcolor=f"rgba(0, 43, 73, {0.06 + idx * 0.02})",
            )
        )
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, max_score], gridcolor=COLORS["mist"]),
        )
    )
    return apply_layout(fig, title=title, height=500)


def heatmap(
    matrix: pd.DataFrame,
    *,
    title: str | None = None,
) -> go.Figure:
    """Heatmap with companies on Y and dimensions on X."""
    if matrix.empty:
        fig = go.Figure()
        fig.add_annotation(text="No matrix data available", showarrow=False)
        return apply_layout(fig, title=title)

    fig = px.imshow(
        matrix,
        color_continuous_scale=["#F8F9FA", "#B5C9DA", "#002B49"],
        aspect="auto",
        labels=dict(color="Score"),
    )
    fig.update_coloraxes(cmin=0, cmax=2)
    return apply_layout(fig, title=title, height=max(360, 40 * len(matrix.index) + 120))


def grouped_bar(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    color: str,
    title: str | None = None,
) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No bar-chart data available", showarrow=False)
        return apply_layout(fig, title=title)
    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color,
        barmode="group",
        color_discrete_sequence=_PALETTE,
    )
    return apply_layout(fig, title=title, height=440)


def distribution(
    df: pd.DataFrame,
    *,
    x: str,
    title: str | None = None,
) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No distribution data available", showarrow=False)
        return apply_layout(fig, title=title)
    fig = px.histogram(
        df,
        x=x,
        nbins=6,
        color_discrete_sequence=[COLORS["navy"]],
    )
    return apply_layout(fig, title=title, height=380)
