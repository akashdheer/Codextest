# Deploying the Company Overview UI on the Internet

## Files in this project
- `company_overview_agent.py`: core logic + ADK tools for company report generation.
- `ui_company_overview.py`: Flask web UI where users type a company name.
- `templates/index.html`: HTML page used by Flask.
- `requirements.txt`: Python packages required by the app.

## Folder structure (keep this layout)

```text
Codextest/
├─ company_overview_agent.py
├─ ui_company_overview.py
├─ requirements.txt
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
6. Add any environment variables required by your ADK/model setup.

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
- For production, disable debug mode and use a production WSGI server.
