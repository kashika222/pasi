# AI document analysis

## Purpose

Take **clean document text** and return **structured JSON** assessments for six
analytics-maturity signal dimensions, each with a **confidence score**.

Uses the **OpenAI API**. Prompts live under ``prompts/`` (not hard-coded in Python).

## Dimensions

| ID | Label |
| --- | --- |
| `leadership_commitment` | Leadership Commitment |
| `talent_investment` | Talent Investment |
| `innovation` | Innovation |
| `analytics_strategy` | Analytics Strategy |
| `ai_strategy` | AI Strategy |
| `digital_transformation` | Digital Transformation |

Score scale: **0** absent · **1** partial · **2** strong.  
Confidence: **0.0–1.0** per dimension, plus `overall_confidence`.

## Prompts (versioned files)

- `prompts/document_analysis_system_v1.txt`
- `prompts/document_analysis_user_v1.txt`

Placeholders use `{{VAR_NAME}}` and are rendered by `pasi.ai.prompts`.

## CLI

```bash
# Set PASI_OPENAI_API_KEY in .env first
uv run pasi analyze \
  --input data/raw/netflix/ten_k/20260806T162420Z_ten_k.json \
  --print-json
```

Outputs are saved to `data/processed/ai/{company_id}/`.

## Python API

```python
from pasi.ai import analyze_document, analyze_text

result = analyze_document("path/to/clean.txt", company_id="netflix")
print(result.to_json_dict())
```

## Output shape (abridged)

```json
{
  "schema_version": "1.0",
  "company_id": "netflix",
  "model_id": "gpt-4o-mini",
  "prompt_version": "document_analysis_v1",
  "status": "success",
  "overall_confidence": 0.74,
  "dimensions": {
    "leadership_commitment": {
      "id": "leadership_commitment",
      "label": "Leadership Commitment",
      "score": 1,
      "confidence": 0.66,
      "evidence_quotes": ["..."],
      "rationale": "..."
    }
  },
  "errors": []
}
```

## Notes

- Long documents are truncated to `PASI_OPENAI_MAX_INPUT_CHARS` (default 120000).
- No dashboard integration in this module.
- Analysis does not scrape the web; it only reads provided clean text / archived JSON.
