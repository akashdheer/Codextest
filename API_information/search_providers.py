"""Search provider layer (Google CSE primary, SerpAPI fallback)."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError

USER_AGENT = "company-overview-adk-agent/3.1"
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
