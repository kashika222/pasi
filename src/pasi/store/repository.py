"""Read API over the PASI DuckDB analytical store."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from pasi.config.settings import Settings, get_settings
from pasi.logging.setup import get_logger
from pasi.store.builder import connect, ensure_store

logger = get_logger(__name__)

# Research-framework categories shown in Company Explorer (map onto AI dims).
FRAMEWORK_CATEGORIES: list[dict[str, Any]] = [
    {
        "id": "leadership_commitment",
        "label": "Leadership Commitment",
        "ai_dimensions": ["leadership_commitment"],
        "description": "Executive sponsorship and leadership language around data/AI.",
    },
    {
        "id": "talent_investment",
        "label": "Talent Investment",
        "ai_dimensions": ["talent_investment"],
        "description": "Hiring, skills, and analytics/AI talent signals.",
    },
    {
        "id": "strategic_communication",
        "label": "Strategic Communication",
        "ai_dimensions": ["analytics_strategy", "ai_strategy"],
        "description": "How the organization communicates analytics and AI strategy.",
    },
    {
        "id": "employee_perception",
        "label": "Employee Perception",
        "ai_dimensions": [],
        "source_types": ["employee_reviews"],
        "description": "Culture and adoption signals from employee-review datasets.",
    },
    {
        "id": "innovation_signals",
        "label": "Innovation Signals",
        "ai_dimensions": ["innovation", "digital_transformation"],
        "description": "Public product, platform, and transformation initiatives.",
    },
]


@dataclass
class StoreRepository:
    """Query helper used by the Streamlit research application."""

    settings: Settings

    @classmethod
    def create(cls, settings: Settings | None = None) -> StoreRepository:
        settings = settings or get_settings()
        ensure_store(settings)
        return cls(settings=settings)

    def _con(self, *, read_only: bool = True):
        return connect(self.settings, read_only=read_only)

    def meta(self) -> dict[str, str]:
        with self._con() as con:
            rows = con.execute("SELECT key, value FROM pipeline_meta").fetchall()
        return {k: v for k, v in rows}

    def companies(self) -> pd.DataFrame:
        with self._con() as con:
            return con.execute(
                """
                SELECT c.*,
                       (SELECT COUNT(*) FROM documents d WHERE d.company_id = c.company_id) AS document_count,
                       (SELECT COUNT(*) FROM analyses a WHERE a.company_id = c.company_id) AS analysis_count
                FROM companies c
                ORDER BY c.name
                """
            ).df()

    def company(self, company_id: str) -> dict[str, Any] | None:
        df = self.companies()
        hit = df[df["company_id"] == company_id]
        if hit.empty:
            return None
        row = hit.iloc[0].to_dict()
        # Pandas uses NaN for SQL NULLs; never surface "nan" in the UI.
        cleaned: dict[str, Any] = {}
        for key, value in row.items():
            if value is None:
                cleaned[key] = None
            elif isinstance(value, float) and value != value:  # NaN check
                cleaned[key] = None
            elif str(value).strip().lower() in {"", "nan", "none", "null"}:
                cleaned[key] = None
            else:
                cleaned[key] = value
        return cleaned

    def documents(
        self,
        *,
        company_id: str | None = None,
        source_type: str | None = None,
    ) -> pd.DataFrame:
        clauses: list[str] = []
        params: list[Any] = []
        if company_id:
            clauses.append("company_id = ?")
            params.append(company_id)
        if source_type:
            clauses.append("source_type = ?")
            params.append(source_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._con() as con:
            return con.execute(
                f"""
                SELECT * FROM documents
                {where}
                ORDER BY company_id, source_type, collected_at DESC NULLS LAST
                """,
                params,
            ).df()

    def analyses(self, *, company_id: str | None = None) -> pd.DataFrame:
        if company_id:
            with self._con() as con:
                return con.execute(
                    """
                    SELECT * FROM analyses
                    WHERE company_id = ?
                    ORDER BY analyzed_at DESC NULLS LAST
                    """,
                    [company_id],
                ).df()
        with self._con() as con:
            return con.execute(
                "SELECT * FROM analyses ORDER BY company_id, analyzed_at DESC NULLS LAST"
            ).df()

    def dimension_scores(self, *, company_id: str | None = None) -> pd.DataFrame:
        if company_id:
            with self._con() as con:
                return con.execute(
                    """
                    SELECT * FROM dimension_scores
                    WHERE company_id = ?
                    """,
                    [company_id],
                ).df()
        with self._con() as con:
            return con.execute("SELECT * FROM dimension_scores").df()

    def latest_company_dimension_matrix(self) -> pd.DataFrame:
        """One row per company × dimension using the latest analysis per source, then averaged."""
        with self._con() as con:
            df = con.execute(
                """
                WITH ranked AS (
                    SELECT ds.*,
                           ROW_NUMBER() OVER (
                               PARTITION BY ds.company_id, ds.source_type, ds.dimension_id
                               ORDER BY a.analyzed_at DESC NULLS LAST
                           ) AS rn
                    FROM dimension_scores ds
                    JOIN analyses a ON a.analysis_id = ds.analysis_id
                    WHERE a.status IN ('success', 'partial')
                )
                SELECT company_id, dimension_id, dimension_label,
                       AVG(score)::DOUBLE AS score,
                       AVG(confidence)::DOUBLE AS confidence,
                       COUNT(*) AS n_sources
                FROM ranked
                WHERE rn = 1
                GROUP BY company_id, dimension_id, dimension_label
                ORDER BY company_id, dimension_id
                """
            ).df()
        return df

    def evidence(
        self,
        *,
        company_id: str | None = None,
        source_type: str | None = None,
        dimension_id: str | None = None,
        search: str | None = None,
    ) -> pd.DataFrame:
        clauses: list[str] = []
        params: list[Any] = []
        if company_id:
            clauses.append("company_id = ?")
            params.append(company_id)
        if source_type:
            clauses.append("source_type = ?")
            params.append(source_type)
        if dimension_id:
            clauses.append("dimension_id = ?")
            params.append(dimension_id)
        if search:
            clauses.append("lower(excerpt) LIKE ?")
            params.append(f"%{search.lower()}%")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._con() as con:
            return con.execute(
                f"""
                SELECT * FROM evidence_items
                {where}
                ORDER BY company_id, source_type, dimension_id
                """,
                params,
            ).df()

    def coverage_summary(self) -> pd.DataFrame:
        with self._con() as con:
            return con.execute(
                """
                SELECT
                    c.company_id,
                    c.name,
                    c.segment,
                    COUNT(DISTINCT d.source_type) AS sources_collected,
                    COUNT(DISTINCT d.doc_id) AS documents,
                    COUNT(DISTINCT a.analysis_id) AS analyses
                FROM companies c
                LEFT JOIN documents d ON d.company_id = c.company_id
                LEFT JOIN analyses a ON a.company_id = c.company_id
                GROUP BY c.company_id, c.name, c.segment
                ORDER BY c.name
                """
            ).df()

    def load_document_payload(self, local_json_path: str) -> dict[str, Any] | None:
        path = Path(local_json_path) if local_json_path else None
        if path is None or not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Could not read document payload %s", local_json_path)
            return None


@lru_cache(maxsize=1)
def get_repository() -> StoreRepository:
    return StoreRepository.create()


def clear_repository_cache() -> None:
    get_repository.cache_clear()
