"""Google ADK agent: Company Overview Provider with Google->SerpAPI fallback."""

from __future__ import annotations

import importlib
import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError

USER_AGENT = "company-overview-adk-agent/3.0"
TIMEOUT_SECONDS = 20
GOOGLE_CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


# # CLASS: SearchResult
# Purpose: store provider, query, and normalized items returned by the selected search API.
@dataclass
class SearchResult:
    """Container for normalized search results."""

    provider: str
    query: str
    items: list[dict[str, Any]]


# # FUNCTION: _safe_get
# Purpose: make safe HTTP GET requests and return JSON dictionary with descriptive errors.
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

        api_message = ""
        reasons: list[str] = []
        if isinstance(parsed, dict):
            google_error = parsed.get("error", {})
            if isinstance(google_error, dict):
                api_message = google_error.get("message") or ""
                for detail in google_error.get("errors", []) or []:
                    reason = detail.get("reason")
                    if reason:
                        reasons.append(reason)
            if not api_message:
                api_message = parsed.get("error") or parsed.get("message") or ""

        message = api_message or str(exc)
        detail_suffix = f" | reason(s): {', '.join(reasons)}" if reasons else ""
        return {
            "error": f"API request failed ({exc.code} {exc.reason}): {message}{detail_suffix}",
            "status_code": exc.code,
            "url": url,
            "params": params or {},
            "raw_response": parsed or body,
        }
    except URLError as exc:
        return {
            "error": f"Network error while calling API: {exc.reason}",
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


# # FUNCTION: _get_serpapi_config
# Purpose: read SerpAPI credentials from environment variables.
def _get_serpapi_config() -> dict[str, str | None]:
    """Return SerpAPI API key from environment."""

    return {"api_key": os.getenv("SERPAPI_API_KEY")}


# # FUNCTION: google_custom_search
# Purpose: perform Google CSE request and return normalized result items.
def google_custom_search(query: str, num_results: int = 5) -> dict[str, Any]:
    """Search Google via Custom Search JSON API."""

    cfg = _get_google_api_config()
    api_key = cfg.get("api_key")
    cse_id = cfg.get("cse_id")
    if not api_key or not cse_id:
        return {
            "provider": "google_cse",
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
        return {
            "provider": "google_cse",
            "error": payload.get("error"),
            "query": query,
            "items": [],
        }

    raw_items = payload.get("items", []) if isinstance(payload, dict) else []
    items = [
        {
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet"),
        }
        for item in raw_items
    ]
    return SearchResult(provider="google_cse", query=query, items=items).__dict__


# # FUNCTION: serpapi_search
# Purpose: perform SerpAPI request and return normalized result items.
def serpapi_search(query: str, num_results: int = 5) -> dict[str, Any]:
    """Search web via SerpAPI (Google engine)."""

    cfg = _get_serpapi_config()
    api_key = cfg.get("api_key")
    if not api_key:
        return {
            "provider": "serpapi",
            "error": "Missing SerpAPI credential. Set SERPAPI_API_KEY as environment variable.",
            "query": query,
            "items": [],
        }

    payload = _safe_get(
        SERPAPI_ENDPOINT,
        params={
            "api_key": api_key,
            "engine": "google",
            "q": query,
            "num": max(1, min(num_results, 10)),
        },
    )

    if payload.get("error"):
        return {
            "provider": "serpapi",
            "error": payload.get("error"),
            "query": query,
            "items": [],
        }

    raw_items = payload.get("organic_results", []) if isinstance(payload, dict) else []
    items = [
        {
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet") or item.get("snippet_highlighted_words", [""])[0],
        }
        for item in raw_items[: max(1, min(num_results, 10))]
    ]
    return SearchResult(provider="serpapi", query=query, items=items).__dict__


# # FUNCTION: search_web
# Purpose: try Google CSE first and automatically fall back to SerpAPI on Google failure.
def search_web(query: str, num_results: int = 5) -> dict[str, Any]:
    """Search web with provider fallback: Google CSE -> SerpAPI."""

    google_result = google_custom_search(query, num_results=num_results)
    if not google_result.get("error"):
        return google_result

    serp_result = serpapi_search(query, num_results=num_results)
    if not serp_result.get("error"):
        serp_result["fallback_from"] = "google_cse"
        serp_result["fallback_reason"] = google_result.get("error")
        return serp_result

    return {
        "provider": "none",
        "query": query,
        "items": [],
        "error": (
            "Both providers failed. "
            f"Google CSE error: {google_result.get('error')} | "
            f"SerpAPI error: {serp_result.get('error')}"
        ),
    }


# # FUNCTION: check_search_api_credentials
# Purpose: validate Google and SerpAPI credentials and show which provider is usable.
def check_search_api_credentials() -> dict[str, Any]:
    """Validate configured search providers with a minimal test query."""

    google = google_custom_search("Microsoft", num_results=1)
    serp = serpapi_search("Microsoft", num_results=1)

    provider_status = {
        "google_cse": {"ok": not bool(google.get("error")), "error": google.get("error")},
        "serpapi": {"ok": not bool(serp.get("error")), "error": serp.get("error")},
    }

    if provider_status["google_cse"]["ok"]:
        return {
            "ok": True,
            "active_provider": "google_cse",
            "provider_status": provider_status,
            "message": "Google CSE is working.",
        }
    if provider_status["serpapi"]["ok"]:
        return {
            "ok": True,
            "active_provider": "serpapi",
            "provider_status": provider_status,
            "message": "Google CSE unavailable; SerpAPI is working as fallback.",
        }

    return {
        "ok": False,
        "provider_status": provider_status,
        "message": "No configured search provider is currently working.",
        "troubleshooting": [
            "For Google CSE: set GOOGLE_API_KEY + GOOGLE_CSE_ID and enable Custom Search API.",
            "For SerpAPI: set SERPAPI_API_KEY and ensure account quota is available.",
            "Verify key restrictions/billing/quota settings for both providers.",
        ],
    }


# # FUNCTION: _join_snippets
# Purpose: combine snippets from search results into a single text block for downstream extraction.
def _join_snippets(items: list[dict[str, Any]]) -> str:
    """Concatenate snippets from search results."""

    return " ".join((item.get("snippet") or "").strip() for item in items if item.get("snippet"))


# # FUNCTION: get_general_overview
# Purpose: fetch general company overview by querying search providers for profile context.
def get_general_overview(company_name: str) -> dict[str, Any]:
    """Fetch company overview from search API results."""

    query = f"{company_name} company overview business summary official website"
    result = search_web(query, num_results=6)
    if result.get("error"):
        return {
            "company_name": company_name,
            "error": result["error"],
            "provider": result.get("provider"),
            "sources": [],
        }

    snippets_text = _join_snippets(result.get("items", []))
    return {
        "company_name": company_name,
        "provider": result.get("provider"),
        "overview_text": snippets_text,
        "sources": result.get("items", []),
        "fallback_from": result.get("fallback_from"),
        "fallback_reason": result.get("fallback_reason"),
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
        "note": "Heuristic extraction from search snippets (Google/SerpAPI).",
    }


# # FUNCTION: get_shareholder_pattern
# Purpose: fetch shareholder-related references using search providers with focused ownership queries.
def get_shareholder_pattern(company_name: str) -> dict[str, Any]:
    """Fetch shareholder pattern references from search API."""

    query = (
        f"{company_name} shareholder pattern major shareholders institutional holders "
        "ownership structure"
    )
    result = search_web(query, num_results=8)
    if result.get("error"):
        return {
            "company_name": company_name,
            "error": result["error"],
            "provider": result.get("provider"),
            "sources": [],
        }

    return {
        "company_name": company_name,
        "provider": result.get("provider"),
        "shareholder_notes": _join_snippets(result.get("items", [])),
        "sources": result.get("items", []),
        "fallback_from": result.get("fallback_from"),
        "fallback_reason": result.get("fallback_reason"),
        "note": "Validate shareholding data with official filings/exchange disclosures.",
    }


# # FUNCTION: build_company_report
# Purpose: orchestrate overview/products/shareholder retrieval and fallback behavior.
def build_company_report(company_name: str) -> dict[str, Any]:
    """Build full report combining overview, products, and shareholder pattern."""

    overview = get_general_overview(company_name)
    if overview.get("error"):
        credential_check = check_search_api_credentials()
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
        "search_provider_used": overview.get("provider"),
    }


# # FUNCTION: create_root_agent
# Purpose: create and return a Google ADK Agent with fallback-enabled search tools.
def create_root_agent():
    """Create and return Google ADK Agent instance."""

    Agent = importlib.import_module("google.adk.agents").Agent
    return Agent(
        name="company_overview_provider",
        model="gemini-2.0-flash",
        description="Provides company overview, products/services, and shareholder pattern.",
        instruction=(
            "You are a company research assistant. "
            "Use search_web/build_company_report to gather overview, products/services, and shareholder info. "
            "Google CSE is primary; SerpAPI is automatic fallback. "
            "Cite source links and mention fallback/limitations."
        ),
        tools=[
            check_search_api_credentials,
            google_custom_search,
            serpapi_search,
            search_web,
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
        print(json.dumps(check_search_api_credentials(), indent=2, default=str))
    else:
        company = arg or "Microsoft"
        print(json.dumps(build_company_report(company), indent=2, default=str))
