"""CLI entrypoint for PASI."""

from __future__ import annotations

import argparse
import json
from typing import Any

from pasi.ai import analyze_document
from pasi.ingest import SourceType, collect_source
from pasi.ingest.companies import load_companies
from pasi.logging.setup import configure_logging, get_logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pasi",
        description="Public Analytics Signal Index (PASI)",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Override log level (DEBUG, INFO, WARNING, ERROR)",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("info", help="Show package status")

    collect = subparsers.add_parser(
        "collect",
        help="Collect a public data source into standardized JSON",
    )
    collect.add_argument(
        "--company",
        required=True,
        help="Company id from configs/companies.yaml, or 'all'",
    )
    collect.add_argument(
        "--source",
        required=True,
        choices=[s.value for s in SourceType],
        help="Source type to collect",
    )
    collect.add_argument(
        "--filing-year",
        type=int,
        default=None,
        help="Optional 10-K filing year filter",
    )
    collect.add_argument(
        "--file-path",
        default=None,
        help="Local file path (earnings transcript or careers HTML)",
    )
    collect.add_argument(
        "--source-url",
        default=None,
        help="Explicit URL for earnings transcript download",
    )
    collect.add_argument(
        "--dataset-path",
        default=None,
        help="Path to packaged employee-review dataset",
    )
    collect.add_argument(
        "--company-filter",
        default=None,
        help="Value used to filter review rows (defaults to company name)",
    )
    collect.add_argument(
        "--company-column",
        default="company",
        help="Column name for company filter in review datasets",
    )
    collect.add_argument(
        "--careers-url",
        default=None,
        help="Override careers URL from companies.yaml",
    )
    collect.add_argument(
        "--allow-fetch",
        action="store_true",
        help="Permit HTTP GET for careers pages (confirm ToS first)",
    )
    collect.add_argument(
        "--no-archive",
        action="store_true",
        help="Do not write JSON under data/raw/",
    )
    collect.add_argument(
        "--print-json",
        action="store_true",
        help="Print standardized JSON document(s) to stdout",
    )

    analyze = subparsers.add_parser(
        "analyze",
        help="Run OpenAI document analysis → structured JSON with confidence scores",
    )
    analyze.add_argument(
        "--input",
        required=True,
        help="Clean text file (.txt/.md/.html) or PASI collection JSON",
    )
    analyze.add_argument(
        "--company",
        default=None,
        help="Optional company id override",
    )
    analyze.add_argument(
        "--company-name",
        default=None,
        help="Optional company name override",
    )
    analyze.add_argument(
        "--source",
        default=None,
        choices=[s.value for s in SourceType],
        help="Optional source type override",
    )
    analyze.add_argument(
        "--no-save",
        action="store_true",
        help="Do not write analysis JSON under data/processed/ai/",
    )
    analyze.add_argument(
        "--print-json",
        action="store_true",
        help="Print analysis JSON to stdout",
    )

    subparsers.add_parser(
        "refresh-store",
        help="Rebuild DuckDB analytical store from data/raw and data/processed/ai",
    )
    return parser


def _company_ids(value: str) -> list[str]:
    if value.lower() == "all":
        return [str(row["id"]) for row in load_companies()]
    return [value]


def _run_collect(args: argparse.Namespace) -> int:
    logger = get_logger(__name__)
    ids = _company_ids(args.company)
    optional = {
        "filing_year": args.filing_year,
        "file_path": args.file_path,
        "source_url": args.source_url,
        "dataset_path": args.dataset_path,
        "company_filter": args.company_filter,
        "company_column": args.company_column,
        "careers_url": args.careers_url,
    }
    kwargs: dict[str, Any] = {
        "archive": not args.no_archive,
        "allow_fetch": bool(args.allow_fetch),
        **{key: value for key, value in optional.items() if value is not None},
    }

    exit_code = 0
    for company_id in ids:
        document = collect_source(
            company_id=company_id,
            source=args.source,
            **kwargs,
        )
        summary = (
            f"{company_id}/{args.source} → {document.status.value}"
            f" errors={len(document.errors)}"
        )
        if document.status.value == "error":
            exit_code = 1
            logger.error("%s | %s", summary, "; ".join(document.errors))
        else:
            logger.info(summary)
        if args.print_json:
            print(json.dumps(document.to_json_dict(), indent=2))
        elif document.metadata.get("archived_json"):
            print(document.metadata["archived_json"])
    return exit_code


def _run_analyze(args: argparse.Namespace) -> int:
    logger = get_logger(__name__)
    result = analyze_document(
        args.input,
        company_id=args.company,
        company_name=args.company_name,
        source_type=args.source,
        save=not args.no_save,
    )
    summary = (
        f"analyze → {result.status} overall_confidence={result.overall_confidence:.2f} "
        f"dims={len(result.dimensions)}"
    )
    if result.status == "error":
        logger.error("%s | %s", summary, "; ".join(result.errors))
        if args.print_json:
            print(json.dumps(result.to_json_dict(), indent=2))
        return 1

    logger.info(summary)
    if args.print_json:
        print(json.dumps(result.to_json_dict(), indent=2))
    elif result.metadata.get("archived_json"):
        print(result.metadata["archived_json"])
    return 0 if result.status == "success" else 0


def _run_refresh_store() -> int:
    from pasi.store import clear_repository_cache, rebuild_store

    logger = get_logger(__name__)
    counts = rebuild_store()
    clear_repository_cache()
    logger.info("Store refresh complete: %s", counts)
    print(json.dumps(counts, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(level=args.log_level)
    logger = get_logger(__name__)

    if args.command is None or args.command == "info":
        logger.info("PASI CLI ready (collect + analyze + refresh-store).")
        print("pasi 0.1.0 — commands: collect, analyze, refresh-store")
        return 0

    if args.command == "collect":
        return _run_collect(args)
    if args.command == "analyze":
        return _run_analyze(args)
    if args.command == "refresh-store":
        return _run_refresh_store()

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
