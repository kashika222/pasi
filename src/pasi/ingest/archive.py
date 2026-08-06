"""Persist collected documents under ``data/raw/``."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pasi.config.settings import Settings, get_settings
from pasi.ingest.schema import CollectedDocument
from pasi.logging.setup import get_logger

logger = get_logger(__name__)


def raw_company_source_dir(
    company_id: str,
    source_type: str,
    settings: Settings | None = None,
) -> Path:
    settings = settings or get_settings()
    path = settings.resolve(settings.data_dir / "raw" / company_id / source_type)
    path.mkdir(parents=True, exist_ok=True)
    return path


def archive_document(
    document: CollectedDocument,
    *,
    settings: Settings | None = None,
    raw_bytes: bytes | None = None,
    raw_suffix: str = ".bin",
) -> Path:
    """Write standardized JSON (and optional raw bytes) to the evidence archive.

    Returns
    -------
    Path
        Path to the written JSON envelope.
    """
    settings = settings or get_settings()
    out_dir = raw_company_source_dir(
        document.company_id,
        document.source_type.value,
        settings=settings,
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"{stamp}_{document.source_type.value}.json"

    payload = document.to_json_dict()
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Archived collection JSON → %s", json_path)

    if raw_bytes is not None:
        raw_path = out_dir / f"{stamp}_{document.source_type.value}_raw{raw_suffix}"
        raw_path.write_bytes(raw_bytes)
        try:
            document.provenance.local_path = str(raw_path.relative_to(settings.repo_root))
        except ValueError:
            document.provenance.local_path = str(raw_path)
        # Re-write JSON so provenance.local_path is stored.
        payload = document.to_json_dict()
        json_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Archived raw bytes → %s", raw_path)

    return json_path
