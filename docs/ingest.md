# Data collection (ingest)

## Purpose

Collect **public** company evidence into a **standardized JSON envelope**
(`CollectedDocument`, schema version `1.0`). No AI analysis happens here.

## Sources

| Source | Module | How it works |
| --- | --- | --- |
| Form 10-K | `pasi.ingest.sec_10k.SecTenKCollector` | Official SEC EDGAR APIs |
| Earnings call | `pasi.ingest.earnings.EarningsTranscriptCollector` | Local file **or** explicit authorized URL |
| Employee reviews | `pasi.ingest.employee_reviews.EmployeeReviewDatasetLoader` | Packaged CSV/JSON/JSONL/Parquet only |
| Careers pages | `pasi.ingest.careers.CareersPageCollector` | Local HTML snapshot **or** opt-in HTTP GET |

## Standardized JSON shape

```json
{
  "schema_version": "1.0",
  "source_type": "ten_k | earnings_call | employee_reviews | careers",
  "company_id": "netflix",
  "company_name": "Netflix",
  "collected_at": "2026-08-06T16:00:00+00:00",
  "status": "success | partial | error",
  "provenance": {
    "method": "sec_edgar_download",
    "license_note": "...",
    "url": "https://...",
    "retrieved_at": "...",
    "content_sha256": "...",
    "local_path": null,
    "http_status": 200
  },
  "metadata": {},
  "content": {},
  "errors": []
}
```

Failed collections still return this envelope with `status=error` and messages in
`errors` (callers should not need try/except for expected failures).

## CLI examples

```bash
# Update PASI_SEC_USER_AGENT in .env with your real academic email first.
uv run pasi collect --company netflix --source ten_k

# Earnings transcript from a manually downloaded file
uv run pasi collect --company netflix --source earnings_call \
  --file-path data/external/netflix_q1_transcript.txt

# Packaged review dataset (no Glassdoor scraping)
uv run pasi collect --company netflix --source employee_reviews \
  --dataset-path data/external/reviews.csv --company-filter Netflix

# Careers from a local HTML snapshot (preferred)
uv run pasi collect --company snowflake --source careers \
  --file-path data/external/snowflake_careers.html

# Careers HTTP fetch only after confirming site terms
uv run pasi collect --company snowflake --source careers --allow-fetch
```

Artifacts are written under:

```text
data/raw/{company_id}/{source_type}/{timestamp}_{source}.json
data/raw/{company_id}/{source_type}/{timestamp}_{source}_raw.*
```

## Python API

```python
from pasi.ingest import collect_source, SourceType

doc = collect_source(company_id="netflix", source=SourceType.TEN_K)
print(doc.status, doc.to_json_dict().keys())
```

## Design notes

- **Modularity:** each source is an independent collector; `collect_source` is a thin orchestrator.
- **Error handling:** collectors catch IO/HTTP failures and return error envelopes; orchestration continues for multi-company runs.
- **Logging:** all collectors use `pasi.logging.get_logger`.
- **Ethics / ToS:** no Glassdoor scraping; careers fetch is opt-in; earnings default to local files.
- **SEC compliance:** set `PASI_SEC_USER_AGENT` to a descriptive string with contact email.
