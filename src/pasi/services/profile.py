"""Business logic for the PASI research application (no Streamlit imports)."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from pasi.store.repository import FRAMEWORK_CATEGORIES, StoreRepository


def company_profile(repo: StoreRepository, company_id: str) -> dict[str, Any]:
    """Assemble an analyst-facing company profile from store tables only."""
    company = repo.company(company_id)
    if company is None:
        return {"error": f"Unknown company_id: {company_id}"}

    docs = repo.documents(company_id=company_id)
    analyses = repo.analyses(company_id=company_id)
    dims = repo.dimension_scores(company_id=company_id)
    evidence = repo.evidence(company_id=company_id)

    matrix = repo.latest_company_dimension_matrix()
    company_dims = matrix[matrix["company_id"] == company_id] if not matrix.empty else matrix

    radar_scores = {
        row["dimension_label"]: float(row["score"])
        for _, row in company_dims.iterrows()
    }

    categories = [_category_block(cat, dims, evidence, docs) for cat in FRAMEWORK_CATEGORIES]

    return {
        "company": company,
        "documents": docs,
        "analyses": analyses,
        "dimension_rows": dims,
        "evidence": evidence,
        "radar_scores": radar_scores,
        "categories": categories,
        "has_analysis": not analyses.empty,
        "has_documents": not docs.empty,
    }


def _category_block(
    cat: dict[str, Any],
    dims: pd.DataFrame,
    evidence: pd.DataFrame,
    docs: pd.DataFrame,
) -> dict[str, Any]:
    ai_dims = cat.get("ai_dimensions") or []
    source_types = cat.get("source_types") or []

    related = (
        dims[dims["dimension_id"].isin(ai_dims)] if ai_dims and not dims.empty else dims.iloc[0:0]
    )
    if source_types and not dims.empty:
        by_source = dims[dims["source_type"].isin(source_types)]
        related = pd.concat([related, by_source]).drop_duplicates()

    if related.empty:
        assessment = "No processed assessment available"
        score = None
        confidence = None
        summary = (
            "This category has not been scored yet. Run AI analysis on relevant "
            "documents, then refresh the analytical store."
        )
        quotes: list[str] = []
        sources: list[str] = []
    else:
        score = float(related["score"].mean())
        confidence = float(related["confidence"].mean())
        assessment = _score_label(score)
        rationales = [r for r in related["rationale"].tolist() if isinstance(r, str) and r.strip()]
        summary = (
            " ".join(rationales[:3])
            if rationales
            else "Assessment available without rationale text."
        )
        quotes = []
        for raw in related["evidence_json"].tolist():
            try:
                items = json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError:
                items = []
            if isinstance(items, list):
                quotes.extend([str(q) for q in items if str(q).strip()])
        sources = sorted(set(related["source_type"].tolist()))

    doc_refs = []
    if not docs.empty:
        subset = docs
        if source_types:
            subset = docs[docs["source_type"].isin(source_types)]
        for _, row in subset.head(5).iterrows():
            doc_refs.append(
                {
                    "source_type": row.get("source_type"),
                    "url": row.get("provenance_url"),
                    "path": row.get("local_json_path"),
                    "filing_date": row.get("filing_date"),
                }
            )

    return {
        "id": cat["id"],
        "label": cat["label"],
        "description": cat["description"],
        "assessment": assessment,
        "score": score,
        "confidence": confidence,
        "ai_summary": summary,
        "evidence_quotes": quotes[:8],
        "source_types": sources,
        "document_refs": doc_refs,
        "available": score is not None,
    }


def _score_label(score: float | None) -> str:
    if score is None:
        return "Unavailable"
    if score < 0.5:
        return "Weak / absent signal"
    if score < 1.5:
        return "Partial signal"
    return "Strong signal"


def comparison_payload(
    repo: StoreRepository,
    company_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build comparison matrices/charts inputs for selected companies."""
    companies = repo.companies()
    matrix = repo.latest_company_dimension_matrix()
    if company_ids:
        companies = companies[companies["company_id"].isin(company_ids)]
        if not matrix.empty:
            matrix = matrix[matrix["company_id"].isin(company_ids)]

    if matrix.empty:
        return {
            "companies": companies,
            "matrix": pd.DataFrame(),
            "long": matrix,
            "radar": {},
            "has_data": False,
        }

    name_map = dict(zip(companies["company_id"], companies["name"], strict=False))
    long_df = matrix.copy()
    long_df["company_name"] = long_df["company_id"].map(name_map)

    pivot = long_df.pivot_table(
        index="company_name",
        columns="dimension_label",
        values="score",
        aggfunc="mean",
    )

    radar: dict[str, dict[str, float]] = {}
    for company_name, group in long_df.groupby("company_name"):
        radar[str(company_name)] = {
            row["dimension_label"]: float(row["score"]) for _, row in group.iterrows()
        }

    return {
        "companies": companies,
        "matrix": pivot,
        "long": long_df,
        "radar": radar,
        "has_data": True,
    }


def evidence_trail(
    repo: StoreRepository,
    *,
    company_id: str | None = None,
    source_type: str | None = None,
    dimension_id: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    """Return explainability chains: excerpt → interpretation → indicator."""
    ev = repo.evidence(
        company_id=company_id,
        source_type=source_type,
        dimension_id=dimension_id,
        search=search,
    )
    trails: list[dict[str, Any]] = []
    for _, row in ev.iterrows():
        trails.append(
            {
                "company_id": row.get("company_id"),
                "source_type": row.get("source_type"),
                "dimension_id": row.get("dimension_id"),
                "excerpt": row.get("excerpt"),
                "interpretation": row.get("rationale"),
                "indicator_score": row.get("score"),
                "confidence": row.get("confidence"),
                "document_path": row.get("document_path"),
                "provenance_url": row.get("provenance_url"),
            }
        )
    return trails


def export_dimension_csv(repo: StoreRepository) -> str:
    """CSV text of latest company × dimension scores."""
    df = repo.latest_company_dimension_matrix()
    if df.empty:
        return "company_id,dimension_id,dimension_label,score,confidence,n_sources\n"
    return df.to_csv(index=False)


def executive_summary_text(profile: dict[str, Any]) -> str:
    """Deterministic executive summary from available profile data only."""
    company = profile.get("company") or {}
    name = company.get("name", "Unknown company")
    lines = [
        f"Executive brief: {name}",
        "",
        f"Segment: {company.get('segment')} | Industry: {company.get('industry')}",
        f"Documents collected: {int(company.get('document_count') or 0)}",
        f"AI analyses available: {int(company.get('analysis_count') or 0)}",
        "",
    ]
    if not profile.get("has_analysis"):
        lines.append(
            "No AI analysis outputs are available for this company yet. "
            "Collect source documents and run `pasi analyze`, then refresh the store."
        )
        return "\n".join(lines)

    lines.append("Category snapshot (from processed AI outputs only):")
    for cat in profile.get("categories") or []:
        if cat.get("available"):
            lines.append(
                f"- {cat['label']}: {cat['assessment']} "
                f"(score={cat['score']:.2f}, confidence={cat['confidence']:.2f})"
            )
        else:
            lines.append(f"- {cat['label']}: insufficient processed evidence")
    lines.extend(
        ["", "This brief does not claim validated internal analytics maturity."]
    )
    return "\n".join(lines)
