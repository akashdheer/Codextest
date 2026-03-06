# Deploying the Company Overview UI on the Internet

## Files in this project
- `company_overview_agent.py`: core logic + ADK tools for company report generation.
- `ui_company_overview.py`: Flask web UI where users type a company name.
- `templates/index.html`: HTML page used by Flask.
- `requirements.txt`: Python packages required by the app.
- `wsgi.py`: production WSGI entrypoint for gunicorn.
- `Procfile`: process command for platforms that read Procfile.
- `render.yaml`: optional Render blueprint with build/start settings.

## Folder structure (keep this layout)

```text
Codextest/
├─ company_overview_agent.py
├─ ui_company_overview.py
├─ requirements.txt
├─ wsgi.py
├─ Procfile
├─ render.yaml
└─ templates/
   └─ index.html
```

## Run locally

```bash
pip install -r requirements.txt
python ui_company_overview.py
```

Open: `http://127.0.0.1:8080`

## Deploy options

### Option 1: Render (easy)
1. Push these files to GitHub.
2. In Render, create a **Web Service** from your GitHub repo.
3. Runtime: Python.
4. Build command:
   ```bash
   pip install -r requirements.txt
   ```
5. Start command:
   ```bash
   python ui_company_overview.py
   ```
6. Add environment variables:
   - `GOOGLE_API_KEY`: Google API key for Custom Search API (primary provider).
   - `GOOGLE_CSE_ID`: Custom Search Engine ID (`cx`) from Google Programmable Search.
   - `SERPAPI_API_KEY`: SerpAPI key (automatic fallback when Google CSE fails).

### Option 2: Railway
1. Connect your GitHub repository.
2. Railway auto-detects Python.
3. Set start command:
   ```bash
   python ui_company_overview.py
   ```

### Option 3: VM (AWS/GCP/Azure)
1. Copy repository to VM.
2. Install Python + dependencies.
3. Run app behind `gunicorn` + `nginx` for production.

## Notes
- This UI can run without ADK server runtime because it calls `build_company_report` directly.
- Core data retrieval uses Google Custom Search API as primary, with automatic SerpAPI fallback.
- Recommended env vars: `GOOGLE_API_KEY`, `GOOGLE_CSE_ID`, and `SERPAPI_API_KEY`.
- For production, disable debug mode and use a production WSGI server.


## Production start option (gunicorn)

If you want a production-style start command, use gunicorn (already added to `requirements.txt`):

```bash
gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
```

- `wsgi.py` exposes the Flask app object as `app`.
- `Procfile` contains the same command for platforms that read it automatically.
- `render.yaml` can be used to provision this service config directly on Render.


## Validate API credentials quickly

Run:

```bash
python company_overview_agent.py --check-api
```

This command returns explicit diagnostics for both providers (`GOOGLE_API_KEY`, `GOOGLE_CSE_ID`, `SERPAPI_API_KEY`) and shows which provider is currently usable.
