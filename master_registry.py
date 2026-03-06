"""Master registry for available APIs, tools, and agent factories."""

from __future__ import annotations

from API_information.search_providers import (
    check_search_api_credentials,
    google_custom_search,
    search_web,
    serpapi_search,
)
from Agent.multi_agents import (
    create_agent_catalog,
    create_dcf_analyzer_agent,
    create_dcf_helper_agent,
    create_master_agent,
    create_news_agent,
    create_research_agent,
    create_semantic_agent,
    create_technical_analyzer_agent,
    create_technical_researcher_agent,
)
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
        "create_agent_catalog": create_agent_catalog,
        "create_research_agent": create_research_agent,
        "create_news_agent": create_news_agent,
        "create_semantic_agent": create_semantic_agent,
        "create_technical_analyzer_agent": create_technical_analyzer_agent,
        "create_technical_researcher_agent": create_technical_researcher_agent,
        "create_dcf_analyzer_agent": create_dcf_analyzer_agent,
        "create_dcf_helper_agent": create_dcf_helper_agent,
        "create_master_agent": create_master_agent,
    },
}
