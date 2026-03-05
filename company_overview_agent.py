"""Google ADK agent: Company Overview Provider."""

from __future__ import annotations

import importlib
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

USER_AGENT = "company-overview-adk-agent/1.0"
TIMEOUT_SECONDS = 20


@dataclass
class CompanyLookupResult:
    """Container for ticker lookup results."""

    input_name: str
    selected_symbol: str | None
    candidates: list[dict[str, Any]]


def _load_yfinance():
    """Load yfinance dynamically.

    Function purpose:
    - Avoid hard dependency failures when package is not installed.
    - Keeps this module importable for users who only want to inspect agent code.
    """

    try:
        return importlib.import_module("yfinance")
    except Exception:
        return None


def _safe_get(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute an HTTP GET request and return parsed JSON."""

    try:
        query = urllib.parse.urlencode(params or {})
        full_url = f"{url}?{query}" if query else url
        req = urllib.request.Request(full_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return {}


def lookup_ticker(company_name: str) -> dict[str, Any]:
    """Get best Yahoo Finance ticker for a company name.

    Function instructions:
    1) Calls Yahoo search API with the provided company name.
    2) Picks first EQUITY result as preferred symbol.
    3) Returns selected symbol and raw candidates for transparency.
    """

    payload = _safe_get(
        "https://query2.finance.yahoo.com/v1/finance/search",
        params={"q": company_name, "quotes_count": 8, "news_count": 0},
    )
    quotes = payload.get("quotes", []) if isinstance(payload, dict) else []

    selected = None
    for quote in quotes:
        if quote.get("quoteType") == "EQUITY" and quote.get("symbol"):
            selected = quote["symbol"]
            break
    if not selected and quotes:
        selected = quotes[0].get("symbol")

    result = CompanyLookupResult(company_name, selected, quotes)
    return result.__dict__


def get_general_overview(symbol: str) -> dict[str, Any]:
    """Fetch broad company profile from Yahoo Finance.

    Function instructions:
    1) Loads yfinance and initializes `Ticker(symbol)`.
    2) Reads `info` dict for profile fields.
    3) Returns general overview content used by the final report.
    """

    yf = _load_yfinance()
    if yf is None:
        return {"error": "Install dependency: pip install yfinance", "symbol": symbol}

    try:
        info = yf.Ticker(symbol).info or {}
    except Exception as exc:
        return {"error": f"Failed to fetch overview: {exc}", "symbol": symbol}

    return {
        "symbol": symbol,
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "website": info.get("website"),
        "employees": info.get("fullTimeEmployees"),
        "market_cap": info.get("marketCap"),
        "summary": info.get("longBusinessSummary"),
    }


def infer_products_from_summary(summary: str | None) -> dict[str, Any]:
    """Infer product/service bullets from text summary.

    Function instructions:
    1) Splits the business summary into sentences.
    2) Filters sentences containing product/service-related keywords.
    3) Returns top unique sentences as product/service hints.
    """

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
        "note": "Heuristic extraction from business summary.",
    }


def get_shareholder_pattern(symbol: str) -> dict[str, Any]:
    """Fetch shareholder pattern (major + institutional holders).

    Function instructions:
    1) Reads `major_holders` from yfinance for high-level ownership split.
    2) Reads `institutional_holders` for top institutions.
    3) Converts tables to JSON-friendly structures.
    """

    yf = _load_yfinance()
    if yf is None:
        return {"error": "Install dependency: pip install yfinance", "symbol": symbol}

    try:
        ticker = yf.Ticker(symbol)
        major_df = ticker.major_holders
        inst_df = ticker.institutional_holders
    except Exception as exc:
        return {"error": f"Failed to fetch holders: {exc}", "symbol": symbol}

    major_holders = major_df.fillna("").values.tolist() if major_df is not None else []
    institutional = (
        inst_df.fillna("").head(15).to_dict("records") if inst_df is not None else []
    )

    return {
        "symbol": symbol,
        "major_holders": major_holders,
        "institutional_holders_top": institutional,
        "note": "Source: Yahoo Finance via yfinance.",
    }


def build_company_report(company_name: str) -> dict[str, Any]:
    """Build full report combining overview, products, and shareholder pattern.

    Function instructions:
    1) Resolves ticker from company name.
    2) Collects overview and extracts product/service highlights.
    3) Collects shareholder pattern and returns final structured JSON.
    """

    lookup = lookup_ticker(company_name)
    symbol = lookup.get("selected_symbol")
    if not symbol:
        return {"company_name": company_name, "error": "Ticker not found", "lookup": lookup}

    overview = get_general_overview(symbol)
    products = infer_products_from_summary(overview.get("summary"))
    holders = get_shareholder_pattern(symbol)

    return {
        "company_name": company_name,
        "ticker": symbol,
        "overview": overview,
        "products": products,
        "shareholder_pattern": holders,
    }


def create_root_agent():
    """Create and return Google ADK Agent instance.

    Function instructions:
    1) Dynamically imports `google.adk.agents.Agent`.
    2) Configures instructions and tool list.
    3) Returns ADK agent object to be used as root agent in your app.
    """

    Agent = importlib.import_module("google.adk.agents").Agent
    return Agent(
        name="company_overview_provider",
        model="gemini-2.0-flash",
        description="Provides company overview, products/services, and shareholder pattern.",
        instruction=(
            "You are a financial research assistant. "
            "When user gives a company name, call build_company_report. "
            "Respond with sections: General Overview, Products/Services, Shareholder Pattern."
        ),
        tools=[
            lookup_ticker,
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
