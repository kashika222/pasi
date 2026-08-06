"""Company registry helpers for ingest."""

from __future__ import annotations

from typing import Any

from pasi.config.loader import load_named_config
from pasi.config.settings import Settings, get_settings


def load_companies(settings: Settings | None = None) -> list[dict[str, Any]]:
    """Return company rows from ``configs/companies.yaml``."""
    data = load_named_config("companies", settings=settings or get_settings())
    companies = data.get("companies", [])
    if not isinstance(companies, list):
        raise ValueError("configs/companies.yaml: 'companies' must be a list")
    return companies


def get_company(company_id: str, settings: Settings | None = None) -> dict[str, Any]:
    """Look up one company by id or raise ``KeyError``."""
    for row in load_companies(settings=settings):
        if row.get("id") == company_id:
            return row
    raise KeyError(f"Unknown company_id: {company_id}")
