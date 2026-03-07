"""Tool layer for building company overview report and LLM-ready final answers."""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any

from API_information.search_providers import check_search_api_credentials, search_web


# # FUNCTION: _join_snippets
# Purpose: combine snippets from search results into a single text block for downstream extraction.
def _join_snippets(items: list[dict[str, Any]]) -> str:
    """Concatenate snippets from search results."""

    return " ".join((item.get("snippet") or "").strip() for item in items if item.get("snippet"))


# # FUNCTION: normalize_company_name
# Purpose: convert natural-language user prompt into a likely company-name string.
def normalize_company_name(user_input: str) -> str:
    """Normalize raw user input to a concise company name.

    Examples:
    - "Give me shareholder pattern of Microsoft" -> "Microsoft"
    - "Microsoft" -> "Microsoft"
    """

    text = (user_input or "").strip()
    if not text:
        return ""

    lowered = text.lower().strip(" ?.!")
    patterns = [
        r"^give me .*? of (?P<name>.+)$",
        r"^what is .*? of (?P<name>.+)$",
        r"^tell me .*? about (?P<name>.+)$",
        r"^show .*? for (?P<name>.+)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, lowered)
        if match:
            name = match.group("name")
            return " ".join(w.capitalize() for w in name.split())

    return text.strip(" ?.!")


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

    company_name = normalize_company_name(company_name)
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


# # FUNCTION: build_llm_context
# Purpose: convert structured report into concise LLM-ready context text.
def build_llm_context(report: dict[str, Any]) -> str:
    """Convert structured report to a prompt-friendly context block."""

    return json.dumps(report, indent=2, ensure_ascii=False)


# # FUNCTION: generate_llm_answer
# Purpose: call Gemini API using prepared evidence context and return human-readable answer text.
def generate_llm_answer(report: dict[str, Any], user_query: str | None = None) -> dict[str, Any]:
    """Generate final answer text from gathered evidence via Gemini REST API."""

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {
            "error": "GOOGLE_API_KEY is missing for LLM synthesis.",
            "answer": "I fetched evidence but cannot synthesize final answer because GOOGLE_API_KEY is not set.",
        }

    model = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    prompt = (
        "You are a financial research assistant. Use the provided evidence JSON to answer user request. "
        "Write clean markdown with sections: Overview, Products/Services, Shareholder Pattern, "
        "and Key Risks/Unknowns. Do not dump raw JSON.\n\n"
        f"User request: {user_query or report.get('company_name','Company overview')}\n\n"
        f"Evidence JSON:\n{build_llm_context(report)}"
    )

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={urllib.parse.quote(api_key)}"
    )
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ]
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            parsed = json.loads(response.read().decode("utf-8"))
        text = (
            parsed.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )
        if not text:
            return {
                "error": "LLM returned empty text.",
                "answer": "Evidence was collected, but LLM response was empty.",
            }
        return {"answer": text, "model": model}
    except Exception as exc:
        return {
            "error": f"LLM API call failed: {exc}",
            "answer": "Evidence was collected, but final LLM synthesis failed.",
        }


# # FUNCTION: build_company_response
# Purpose: complete pipeline: search evidence + LLM synthesis for end-user readable output.
def build_company_response(user_input: str) -> dict[str, Any]:
    """Return evidence and final synthesized answer for UI/agent usage."""

    company_name = normalize_company_name(user_input)
    report = build_company_report(company_name)
    synthesis = generate_llm_answer(report, user_query=user_input)
    return {
        "company_name": company_name,
        "final_answer": synthesis.get("answer"),
        "llm_error": synthesis.get("error"),
        "llm_model": synthesis.get("model"),
        "report": report,
    }
