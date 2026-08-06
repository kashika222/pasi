#!/usr/bin/env bash
# Batch-analyze the latest successful collection JSON for each company.
# Requires PASI_OPENAI_API_KEY (or PASI_LLM_API_KEY) in .env
set -euo pipefail
cd "$(dirname "$0")/.."

if ! uv run python -c "from pasi.config.settings import get_settings; get_settings.cache_clear(); s=get_settings(); raise SystemExit(0 if (s.openai_api_key or s.llm_api_key) else 1)"; then
  echo "Missing API key. Set PASI_OPENAI_API_KEY in .env, then re-run."
  exit 1
fi

mapfile -t files < <(find data/raw -name '*.json' ! -name '*_analysis.json' | sort)
for f in "${files[@]}"; do
  # Skip error envelopes
  if uv run python -c "import json,sys; d=json.load(open(sys.argv[1])); raise SystemExit(0 if d.get('status')!='error' else 1)" "$f"; then
    echo "=== Analyzing $f ==="
    uv run pasi analyze --input "$f" || echo "FAILED $f"
  else
    echo "=== Skipping error envelope $f ==="
  fi
done

uv run pasi refresh-store
echo "Done. Restart or refresh the Streamlit app."
