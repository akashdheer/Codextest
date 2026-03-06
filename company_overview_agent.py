"""Google ADK agent: Company Overview Provider (Google Search API based)."""

from __future__ import annotations

import importlib
import json
import os
import re
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
from dataclasses import dataclass
from typing import Any

USER_AGENT = "company-overview-adk-agent/2.0"
TIMEOUT_SECONDS = 20
GOOGLE_CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"


# # CLASS: GoogleSearchResult
# Purpose: store search query and normalized top results returned by Google Custom Search API.
@dataclass
class GoogleSearchResult:
    """Container for Google search results."""

    query: str
    items: list[dict[str, Any]]


# # FUNCTION: _safe_get
# Purpose: make safe HTTP GET requests and return JSON dictionary (or error structure).
def _safe_get(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute an HTTP GET request and return parsed JSON."""

    try:
        query = urllib.parse.urlencode(params or {})
        full_url = f"{url}?{query}" if query else url
        req = urllib.request.Request(full_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = ""
        parsed: dict[str, Any] = {}
        try:
            body = exc.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
        except Exception:
            parsed = {}

        google_error = parsed.get("error", {}) if isinstance(parsed, dict) else {}
        message = google_error.get("message") or str(exc)
        reasons = []
        for detail in google_error.get("errors", []):
            reason = detail.get("reason")
            if reason:
                reasons.append(reason)

        detail_suffix = f" | reason(s): {', '.join(reasons)}" if reasons else ""
        return {
            "error": f"Google API request failed ({exc.code} {exc.reason}): {message}{detail_suffix}",
            "status_code": exc.code,
            "url": url,
            "params": params or {},
            "raw_response": parsed or body,
        }
    except URLError as exc:
        return {
            "error": f"Network error while calling Google API: {exc.reason}",
            "url": url,
            "params": params or {},
        }
    except Exception as exc:
        return {
            "error": f"Unexpected request error: {exc}",
            "url": url,
            "params": params or {},
        }


# # FUNCTION: _get_google_api_config
# Purpose: read Google API credentials from environment variables used by Custom Search API.
def _get_google_api_config() -> dict[str, str | None]:
    """Return Google API key and CSE ID from environment."""

    return {
        "api_key": os.getenv("GOOGLE_API_KEY"),
        "cse_id": os.getenv("GOOGLE_CSE_ID"),
    }


# # FUNCTION: google_custom_search
# Purpose: perform a Google Custom Search API request and return normalized result items.
def google_custom_search(query: str, num_results: int = 5) -> dict[str, Any]:
    """Search Google via Custom Search JSON API.

    Function instructions:
    1) Reads `GOOGLE_API_KEY` and `GOOGLE_CSE_ID` from environment.
    2) Calls Google Custom Search endpoint for the provided query.
    3) Normalizes top results into title/link/snippet fields.
    """

    cfg = _get_google_api_config()
    api_key = cfg.get("api_key")
    cse_id = cfg.get("cse_id")
    if not api_key or not cse_id:
        return {
            "error": (
                "Missing Google API credentials. Set GOOGLE_API_KEY and GOOGLE_CSE_ID "
                "as environment variables."
            ),
            "query": query,
            "items": [],
        }

    payload = _safe_get(
        GOOGLE_CSE_ENDPOINT,
        params={
            "key": api_key,
            "cx": cse_id,
            "q": query,
            "num": max(1, min(num_results, 10)),
        },
    )

    if payload.get("error") and not payload.get("items"):
        return {"error": payload.get("error"), "query": query, "items": []}

    raw_items = payload.get("items", []) if isinstance(payload, dict) else []
    items = [
        {
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet"),
        }
        for item in raw_items
    ]
    return GoogleSearchResult(query=query, items=items).__dict__


# # FUNCTION: check_google_api_credentials
# Purpose: verify GOOGLE_API_KEY and GOOGLE_CSE_ID are valid and provide debugging details.
def check_google_api_credentials() -> dict[str, Any]:
    """Validate Google API credentials with a lightweight test query.

    Function instructions:
    1) Ensures required env vars are present.
    2) Executes a minimal Google Custom Search request.
    3) Returns explicit success/failure diagnostics for troubleshooting.
    """

    cfg = _get_google_api_config()
    api_key = cfg.get("api_key")
    cse_id = cfg.get("cse_id")

    if not api_key or not cse_id:
        missing = []
        if not api_key:
            missing.append("GOOGLE_API_KEY")
        if not cse_id:
            missing.append("GOOGLE_CSE_ID")
        return {
            "ok": False,
            "error": (
                "Missing required environment variable(s): "
                + ", ".join(missing)
                + ". Add them in your host dashboard and redeploy."
            ),
        }

    payload = _safe_get(
        GOOGLE_CSE_ENDPOINT,
        params={"key": api_key, "cx": cse_id, "q": "Microsoft", "num": 1},
    )

    if payload.get("error"):
        return {
            "ok": False,
            "error": payload.get("error"),
            "troubleshooting": [
                "Ensure Custom Search API is enabled for the same Google Cloud project as your API key.",
                "Ensure API key restrictions allow Custom Search API usage.",
                "Ensure GOOGLE_CSE_ID (cx) is copied correctly from Programmable Search Engine settings.",
                "Ensure billing and quota are active in Google Cloud.",
            ],
        }

    items = payload.get("items", []) if isinstance(payload, dict) else []
    return {
        "ok": True,
        "message": "Google API credentials look valid.",
        "sample_result_count": len(items),
    }


# # FUNCTION: _join_snippets
# Purpose: combine snippets from Google results into a single text block for downstream extraction.
def _join_snippets(items: list[dict[str, Any]]) -> str:
    """Concatenate snippets from search results."""

    return " ".join((item.get("snippet") or "").strip() for item in items if item.get("snippet"))


# # FUNCTION: get_general_overview
# Purpose: fetch general company overview by querying Google API for company profile context.
def get_general_overview(company_name: str) -> dict[str, Any]:
    """Fetch company overview from Google Search API results."""

    query = f"{company_name} company overview business summary official website"
    result = google_custom_search(query, num_results=6)
    if result.get("error"):
        return {"company_name": company_name, "error": result["error"], "sources": []}

    snippets_text = _join_snippets(result.get("items", []))
    return {
        "company_name": company_name,
        "overview_text": snippets_text,
        "sources": result.get("items", []),
    }


# # FUNCTION: infer_products_from_summary
# Purpose: infer product/service bullets from aggregated overview snippet text.
def infer_products_from_summary(summary: str | None) -> dict[str, Any]:
    """Infer product/service bullets from text summary."""

    if not summary:
        return {"products_or_services": [], "note": "No summary text available."}

    keywords = [
        "product",
        "products",
        "service",
        "services",
        "platform",
        "software",
        "hardware",
        "solution",
        "solutions",
        "manufactures",
        "sells",
        "provides",
        "offers",
    ]
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", summary) if s.strip()]
    matched = [s for s in sentences if any(k in s.lower() for k in keywords)]
    return {
        "products_or_services": list(dict.fromkeys(matched))[:8],
        "note": "Heuristic extraction from Google search snippets.",
    }


# # FUNCTION: get_shareholder_pattern
# Purpose: fetch shareholder-related references using Google API with focused ownership queries.
def get_shareholder_pattern(company_name: str) -> dict[str, Any]:
    """Fetch shareholder pattern references from Google Search API."""

    query = (
        f"{company_name} shareholder pattern major shareholders institutional holders "
        "ownership structure"
    )
    result = google_custom_search(query, num_results=8)
    if result.get("error"):
        return {"company_name": company_name, "error": result["error"], "sources": []}

    return {
        "company_name": company_name,
        "shareholder_notes": _join_snippets(result.get("items", [])),
        "sources": result.get("items", []),
        "note": "Validate shareholding data with official filings/exchange disclosures.",
    }


# # FUNCTION: build_company_report
# Purpose: orchestrate overview/products/shareholder retrieval entirely from Google API searches.
def build_company_report(company_name: str) -> dict[str, Any]:
    """Build full report combining overview, products, and shareholder pattern."""

    overview = get_general_overview(company_name)
    if overview.get("error"):
        credential_check = check_google_api_credentials()
        return {
            "company_name": company_name,
            "error": overview["error"],
            "credential_check": credential_check,
        }

    products = infer_products_from_summary(overview.get("overview_text"))
    shareholders = get_shareholder_pattern(company_name)

    return {
        "company_name": company_name,
        "overview": overview,
        "products": products,
        "shareholder_pattern": shareholders,
    }


# # FUNCTION: create_root_agent
# Purpose: create and return a Google ADK Agent with Google-API-based tools and instructions.
def create_root_agent():
    """Create and return Google ADK Agent instance."""

    Agent = importlib.import_module("google.adk.agents").Agent
    return Agent(
        name="company_overview_provider",
        model="gemini-2.0-flash",
        description="Provides company overview, products/services, and shareholder pattern.",
        instruction=(
            "You are a company research assistant. "
            "Use Google API tool functions to gather overview, products/services, and shareholder info. "
            "Cite source links from returned results and mention limitations."
        ),
        tools=[
            check_google_api_credentials,
            google_custom_search,
            get_general_overview,
            infer_products_from_summary,
            get_shareholder_pattern,
            build_company_report,
        ],
    )


if __name__ == "__main__":
    import sys

    arg = " ".join(sys.argv[1:]).strip()
    if arg == "--check-api":
        print(json.dumps(check_google_api_credentials(), indent=2, default=str))
    else:
        company = arg or "Microsoft"
        print(json.dumps(build_company_report(company), indent=2, default=str))
