"""Google ADK agent: Company Overview Provider (Google Search API based)."""

from __future__ import annotations

import importlib
import json
import os
import re
import urllib.parse
import urllib.request
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
    except Exception as exc:
        return {"error": str(exc), "url": url, "params": params or {}}


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
        return {"company_name": company_name, "error": overview["error"]}

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
            google_custom_search,
            get_general_overview,
            infer_products_from_summary,
            get_shareholder_pattern,
            build_company_report,
        ],
    )


if __name__ == "__main__":
    import sys

    company = " ".join(sys.argv[1:]).strip() or "Microsoft"
    print(json.dumps(build_company_report(company), indent=2, default=str))
