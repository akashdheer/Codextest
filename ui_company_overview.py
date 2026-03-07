"""Interactive web UI for company overview agent.

Run locally:
    pip install -r requirements.txt
    python ui_company_overview.py
Then open http://127.0.0.1:8080
"""

from __future__ import annotations

import os

from flask import Flask, render_template, request

from company_overview_agent import build_company_response

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def home():
    """Render input form and synthesized company response."""

    company_name = ""
    response_payload = None
    if request.method == "POST":
        company_name = (request.form.get("company_name") or "").strip()
        if company_name:
            response_payload = build_company_response(company_name)
    return render_template(
        "index.html",
        company_name=company_name,
        response_payload=response_payload,
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
