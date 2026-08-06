#!/usr/bin/env python3
"""Build a slim document catalog for Streamlit Cloud (no full filing text)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "catalog" / "documents.jsonl"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = 0
    with OUT.open("w", encoding="utf-8") as handle:
        for path in sorted(RAW.rglob("*.json")):
            if path.name.endswith("_analysis.json"):
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict) or payload.get("status") == "error":
                continue
            if "source_type" not in payload:
                continue
            provenance = payload.get("provenance") or {}
            content = payload.get("content") or {}
            metadata = payload.get("metadata") or {}
            company_id = payload.get("company_id") or path.parent.parent.name
            record = {
                "company_id": company_id,
                "company_name": payload.get("company_name"),
                "source_type": payload.get("source_type"),
                "status": payload.get("status"),
                "collected_at": payload.get("collected_at"),
                "filing_date": metadata.get("filing_date") or metadata.get("call_date"),
                "provenance_url": provenance.get("url"),
                "provenance_method": provenance.get("method"),
                "content_sha256": provenance.get("content_sha256"),
                "char_count": content.get("char_count"),
                "metadata": metadata,
                "local_json_path": str(path.relative_to(ROOT)),
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            rows += 1
    print(f"Wrote {rows} catalog rows → {OUT}")


if __name__ == "__main__":
    main()
