# Research application

## Purpose

A Streamlit **research platform** (not a KPI dashboard) for exploring PASI
pipeline outputs with evidence-linked explanations.

## Architecture

| Layer | Package | Responsibility |
| --- | --- | --- |
| UI | `app/` + `pasi.ui` | Streamlit pages and shared chrome |
| Business logic | `pasi.services` | Profiles, comparison, evidence trails, exports |
| Visualizations | `pasi.viz` | Plotly charts + professional theme |
| Database | `pasi.store` | DuckDB index over pipeline artifacts |
| Configuration | `configs/` + `pasi.config` | Cohort, sources, settings |

## Pages

1. **Home** — research question, cohort, sources, methodology summary  
2. **Company Explorer** — five framework categories with assessment / evidence / AI summary / sources  
3. **Cross Company Comparison** — radar, heatmap, bars, distribution  
4. **Evidence Explorer** — excerpt → interpretation → indicator  
5. **Methodology** — pipeline, prompts, limitations  

## Run

```bash
uv sync
uv run pasi refresh-store
uv run streamlit run app/Home.py
```

The UI reads **only** indexed pipeline outputs. Missing analyses appear as unavailable.
Scores are never invented.
