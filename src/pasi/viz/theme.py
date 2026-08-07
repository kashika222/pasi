"""Professional visualization theme and Plotly chart builders."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Stitch "Executive Insight System" — modern corporate palette.
COLORS = {
    "navy": "#1E293B",
    "navy_deep": "#091426",
    "ink": "#191C1E",
    "slate": "#45474C",
    "steel": "#94A3B8",
    "mist": "#E2E8F0",
    "paper": "#F8FAFC",
    "surface": "#F7F9FB",
    "indigo": "#6366F1",
    "indigo_deep": "#4648D4",
    "accent": "#6366F1",
    "accent_soft": "#C0C1FF",
    "cyan": "#0099D9",
    "success": "#10B981",
    "success_bg": "#D1FAE5",
    "success_text": "#047857",
    "danger": "#F43F5E",
    "danger_bg": "#FFE4E6",
    "danger_text": "#BE123C",
    "neutral_bg": "#F1F5F9",
    "neutral_text": "#334155",
    "warn": "#F43F5E",
    "muted": "#94A3B8",
}

SCORE_COLORS = {
    0: "#F43F5E",
    1: "#6366F1",
    2: "#10B981",
}

_PALETTE = [
    COLORS["indigo"],
    COLORS["success"],
    COLORS["cyan"],
    COLORS["navy"],
    COLORS["steel"],
    COLORS["accent_soft"],
]


def apply_layout(fig: go.Figure, *, title: str | None = None, height: int = 420) -> go.Figure:
    fig.update_layout(
        title=dict(
            text=title or "",
            font=dict(size=16, color=COLORS["navy"], family="Playfair Display, Georgia, serif"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Helvetica, Arial, sans-serif", color=COLORS["slate"], size=12),
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
            fillcolor="rgba(99, 102, 241, 0.15)",
            line=dict(color=COLORS["indigo"], width=2),
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
                fillcolor=f"rgba(99, 102, 241, {0.05 + idx * 0.03})",
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
    if matrix.empty:
        fig = go.Figure()
        fig.add_annotation(text="No matrix data available", showarrow=False)
        return apply_layout(fig, title=title)

    fig = px.imshow(
        matrix,
        color_continuous_scale=["#FFE4E6", "#F1F5F9", "#D1FAE5"],
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
        color_discrete_sequence=[COLORS["indigo"]],
    )
    return apply_layout(fig, title=title, height=380)
