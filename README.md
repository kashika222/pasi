# Public Analytics Signal Index (PASI)

Independent study project (MS Business Analytics):

> What Public Signals Reveal About Organizational Analytics Maturity:
> An AI-Assisted Assessment Framework

## Status

**End-to-end research platform ready.** Ingest, AI analysis, DuckDB indexing, and a
Streamlit research application are implemented. Populate more companies via
`pasi collect` / `pasi analyze`, then refresh the store.

- Collection: [docs/ingest.md](docs/ingest.md)
- AI analysis: [docs/ai.md](docs/ai.md)
- Research app: [docs/app.md](docs/app.md)

## Stack

| Item | Choice |
| --- | --- |
| Python | 3.12 |
| Package manager | [uv](https://github.com/astral-sh/uv) |
| Config | YAML (`configs/`) + `pydantic-settings` |
| Logging | stdlib logging via `pasi.logging` |
| Analytical store | DuckDB (`db/pasi.duckdb`, rebuilt on deploy) |
| Dashboard | Streamlit (`app/`) |

## Quick start

```bash
# From the repository root
cp .env.example .env

# Create/.sync the virtual environment (Python 3.12) and install the package
uv sync

# Activate (optional; `uv run` works without activation)
source .venv/bin/activate

# Verify CLI
uv run pasi info
uv run pasi collect --help

# Example: download Netflix 10-K from SEC EDGAR (set PASI_SEC_USER_AGENT first)
# uv run pasi collect --company netflix --source ten_k

# Index artifacts and launch the research platform
uv run pasi refresh-store
uv run streamlit run app/Home.py
```

Pinned dependency export (for environments that cannot use `uv`):

```bash
uv export --no-hashes -o requirements.txt
```

## Repository layout

```
pasi/
├── app/                  # Streamlit multipage app (stubs)
├── configs/              # YAML configuration (companies, sources, rubric, …)
├── data/
│   ├── raw/              # Immutable evidence snapshots
│   ├── interim/          # Cleaned / sectioned text
│   ├── processed/        # Features and scores
│   └── external/         # Licensed third-party datasets
├── db/                   # SQLite analytical mart (generated)
├── logs/                 # Runtime logs (gitignored contents)
├── notebooks/            # Exploration only (not official scoring)
├── prompts/              # Versioned LLM prompt templates
├── reports/              # Executive report artifacts
├── scripts/              # Thin CLI wrappers
├── src/pasi/             # Installable Python package
│   ├── ai/
│   ├── clean/
│   ├── config/           # Settings + YAML loaders
│   ├── ingest/
│   ├── logging/          # Logging setup
│   ├── nlp/
│   ├── qa/
│   ├── score/
│   ├── store/
│   └── viz/
└── tests/
```

## Deploy (Streamlit Cloud)

See [docs/DEPLOY.md](docs/DEPLOY.md).

```bash
uv run python scripts/build_document_catalog.py
# then push to GitHub and deploy with main file: app/Home.py
```

## Configuration

- **Environment:** `.env` (see `.env.example`)
- **Research configs:** `configs/*.yaml`
- **Runtime settings:** `pasi.config.settings.Settings`

## Logging

Call `configure_logging()` once at process start (CLI / Streamlit entrypoints).
Logs write to stderr and `logs/pasi.log` by default.

## Cohort (planned)

Snowflake, Databricks, Netflix, Uber, Airbnb, Spotify, Ford, Eli Lilly,
Amplitude, Capital One.

## License

MIT (scaffold). Respect source ToS and dataset licenses for all evidence you add.
