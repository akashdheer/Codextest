"""WSGI entrypoint for production servers (gunicorn)."""

from ui_company_overview import app

# Expose `app` for: gunicorn wsgi:app
