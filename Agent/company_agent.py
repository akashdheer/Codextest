"""Agent factory module for company overview provider."""

from __future__ import annotations

import importlib

from API_information.search_providers import (
    check_search_api_credentials,
    google_custom_search,
    search_web,
    serpapi_search,
)
from Tools.company_tools import (
    build_company_report,
    get_general_overview,
    get_shareholder_pattern,
    infer_products_from_summary,
)


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
