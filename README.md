# Company Overview Provider (v0.1 baseline)

This project is a company-research assistant with:
- a Flask web UI,
- tool functions for report generation,
- API provider integrations (Google CSE + SerpAPI fallback),
- a Google ADK agent factory.

## What the agent can do right now

Given a company name, the system can:
1. Build a **general overview** from web search snippets.
2. Infer **products/services** using heuristic sentence extraction.
3. Build **shareholder-pattern notes** from ownership-related search queries.
4. Automatically use **Google Custom Search API first** and **fallback to SerpAPI** if Google fails.
5. Return explicit credential diagnostics via `--check-api`.

## Project structure and what each file does

- `company_overview_agent.py`
  - Backward-compatible entrypoint and CLI.
  - Re-exports key functions so old imports still work.

- `master_registry.py`
  - Central registry listing available APIs, tools, and agent factory.

- `API_information/search_providers.py`
  - API integrations and provider selection logic.
  - Contains Google CSE search, SerpAPI search, fallback orchestration, and credential checks.

- `Tools/company_tools.py`
  - Business/report logic.
  - Builds overview/products/shareholder sections and final report payload.

- `Agent/company_agent.py`
  - Google ADK `create_root_agent()` factory.
  - Wires tools + API functions into the ADK agent.

- `ui_company_overview.py`
  - Flask UI controller (GET/POST endpoint).

- `templates/index.html`
  - UI page template.

- `wsgi.py`
  - Production WSGI app export for Gunicorn.

- `render.yaml`, `Procfile`, `DEPLOYMENT.md`
  - Deployment configuration and instructions.

- `requirements.txt`
  - Python dependencies.

## Required environment variables

- `GOOGLE_API_KEY`
- `GOOGLE_CSE_ID`
- `SERPAPI_API_KEY`
- `LLM_MODEL` (optional, default: `gemini-1.5-flash`)

> Recommended: set all three for best reliability (Google primary + SerpAPI fallback).

## Quick start

```bash
pip install -r requirements.txt
python ui_company_overview.py
```

Open: `http://127.0.0.1:8080`

The UI now shows an **LLM-synthesized answer** (not just raw API JSON), plus an optional debug evidence block.

## Validate API configuration

```bash
python company_overview_agent.py --check-api
```

## Save this baseline as Git version 0.1

From your project root:

```bash
# confirm working tree is clean
git status

# create annotated tag for baseline
git tag -a v0.1 -m "Baseline v0.1: modular company overview agent (Google CSE + SerpAPI fallback)"

# verify tag exists
git tag --list

# push branch and tag to remote
git push origin work
git push origin v0.1
```

If your default branch is `main`, replace `work` with `main`.

## Suggested next enhancements

- Add source-quality scoring and confidence scores.
- Add caching for repeated company queries.
- Add downloadable report exports (PDF/CSV).
- Add structured sections for risks, competitors, and leadership.


## Agent roles available now

- `Research Agent`: company profile, products, ownership, sectors, and geographies.
- `News Agent`: news, upcoming/past projects, product demand-supply signals.
- `Semantic Agent`: positive/negative interpretation and promise-vs-delivery review.
- `Technical Analyzer`: metric-focused extraction and technical-number analysis.
- `Technical Researcher`: deeper technical research synthesis.
- `DCF Analyzer`: DCF-style scenario framing from available evidence.
- `DCF Helper`: guidance for missing DCF inputs and assumptions.
- `Master Agent`: orchestration layer coordinating all specialist agents.

Implementation is in `Agent/multi_agents.py`, while `Agent/company_agent.py` keeps backward compatibility via `create_root_agent()`.
