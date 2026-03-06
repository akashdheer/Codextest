"""Master registry for available APIs, tools, and agent factory."""

from __future__ import annotations

from API_information.search_providers import (
    check_search_api_credentials,
    google_custom_search,
    search_web,
    serpapi_search,
)
from Agent.company_agent import create_root_agent
from Tools.company_tools import (
    build_company_report,
    get_general_overview,
    get_shareholder_pattern,
    infer_products_from_summary,
)

MASTER_REGISTRY = {
    "apis": {
        "google_custom_search": google_custom_search,
        "serpapi_search": serpapi_search,
        "search_web": search_web,
        "check_search_api_credentials": check_search_api_credentials,
    },
    "tools": {
        "get_general_overview": get_general_overview,
        "infer_products_from_summary": infer_products_from_summary,
        "get_shareholder_pattern": get_shareholder_pattern,
        "build_company_report": build_company_report,
    },
    "agents": {
        "create_root_agent": create_root_agent,
    },
}
