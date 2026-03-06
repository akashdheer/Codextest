"""Tool layer for building company overview report from normalized search data."""

from __future__ import annotations

import re
from typing import Any

from API_information.search_providers import check_search_api_credentials, search_web


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
