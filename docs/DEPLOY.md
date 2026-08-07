# Deploying PASI to Streamlit Community Cloud

## What gets deployed

- App code (`app/`, `src/pasi/`)
- Configs + prompts
- AI analyses (`data/processed/ai/`)
- Slim document catalog (`data/catalog/documents.jsonl`) — **no full 10-K text**

Secrets (`.env`) are **not** committed. The public demo is read-only and does not need Gemini/OpenAI keys.

## One-time prep (local)

```bash
cd ~/Documents/Purdue/Projects/pasi
uv run python scripts/build_document_catalog.py
uv run pasi refresh-store
```

## Push to GitHub

If you have the GitHub CLI:

```bash
git add -A
git status   # confirm .env and data/raw filings are NOT listed
git commit -m "Prepare PASI for Streamlit Cloud deploy"
git branch -M main
gh repo create pasi --public --source=. --remote=origin --push
```

Without `gh`: create an empty repo at [github.com/new](https://github.com/new) named `pasi`, then:

```bash
git remote add origin https://github.com/<YOUR_USER>/pasi.git
git push -u origin main
```

## Streamlit Cloud

1. Go to [https://share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
2. **New app**
3. Select your `pasi` repo
4. Settings:
   - **Main file path:** `app/Home.py`
   - **Python version:** 3.12 (if prompted)
5. Deploy

Optional secrets (only if you later add in-app analysis) — App settings → Secrets:

```toml
PASI_LLM_PROVIDER = "gemini"
PASI_GEMINI_API_KEY = "..."
```

## After deploy

Open the app URL Streamlit gives you. First load rebuilds DuckDB from committed analyses + catalog into `/tmp/pasi.duckdb` (Cloud-safe). Use **Refresh analytical store** in the sidebar if charts look empty.

If you see `duckdb.ConnectionException`, redeploy after pulling the latest `main` (Cloud needs the `/tmp` DuckDB path fix).
