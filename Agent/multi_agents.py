"""Specialized and orchestration agent factories for company intelligence workflows.

This module defines multiple role-based agents:
- Research Agent
- News Agent
- Semantic Agent
- Technical Analyzer
- Technical Researcher
- DCF Analyzer
- DCF Helper
- Master Agent (orchestrator)

All factories return Google ADK `Agent` instances configured with role-specific
instructions and shared tool functions.
"""

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


def _agent_cls():
    """Load and return the Google ADK Agent class dynamically."""

    return importlib.import_module("google.adk.agents").Agent


# # FUNCTION: create_research_agent
# Purpose: build an agent that performs broad company research and business profiling.
def create_research_agent():
    """Create the Research Agent.

    Capabilities:
    - Identifies what a company does.
    - Extracts products/services and operating fields.
    - Infers ownership/shareholder context.
    - Surfaces countries/regions of operation from available web snippets.
    """

    Agent = _agent_cls()
    return Agent(
        name="research_agent",
        model="gemini-2.0-flash",
        description="Performs broad company research (business, products, owners, sectors, geography).",
        instruction=(
            "You are the Research Agent. Build a structured company research brief. "
            "Answer: what company does, products/services, owners/shareholders, fields/industries, "
            "countries of operation. Use tool outputs and include source links and unknowns clearly."
        ),
        tools=[
            search_web,
            get_general_overview,
            infer_products_from_summary,
            get_shareholder_pattern,
            build_company_report,
        ],
    )


# # FUNCTION: create_news_agent
# Purpose: build an agent focused on news, projects, and demand/supply news signals.
def create_news_agent():
    """Create the News Agent.

    Capabilities:
    - Finds company-related news.
    - Extracts prior delivered projects and upcoming projects.
    - Tracks product news and supply-demand shift signals globally.
    """

    Agent = _agent_cls()
    return Agent(
        name="news_agent",
        model="gemini-2.0-flash",
        description="Finds and summarizes company/project/product news with market-shift context.",
        instruction=(
            "You are the News Agent. Collect and summarize relevant company news, upcoming projects, "
            "previously delivered projects, and product-level demand/supply shifts. "
            "Use search tools, provide timeline-style bullets, and cite source links."
        ),
        tools=[search_web, google_custom_search, serpapi_search],
    )


# # FUNCTION: create_semantic_agent
# Purpose: build an agent that evaluates sentiment, outcomes, and promise-vs-delivery from news context.
def create_semantic_agent():
    """Create the Semantic Agent.

    Capabilities:
    - Infers positive/negative sentiment from news context.
    - Evaluates whether promised initiatives were delivered.
    - Highlights inconsistencies and risk/opportunity signals.
    """

    Agent = _agent_cls()
    return Agent(
        name="semantic_agent",
        model="gemini-2.0-flash",
        description="Interprets news semantics: sentiment, risk, promise-vs-delivery evaluation.",
        instruction=(
            "You are the Semantic Agent. Based on available news/research evidence, provide balanced "
            "positive and negative interpretation, then evaluate promise-vs-delivery. "
            "Mark assumptions and missing proof explicitly."
        ),
        tools=[search_web, build_company_report],
    )


# # FUNCTION: create_technical_analyzer_agent
# Purpose: build an agent that collects and reasons about technical/financial numeric indicators.
def create_technical_analyzer_agent():
    """Create the Technical Analyzer Agent.

    Capabilities:
    - Gathers available numeric/financial indicators from internet sources.
    - Analyzes sales, market cap, earnings, and related figures where discoverable.
    - Summarizes what is measurable vs unavailable.
    """

    Agent = _agent_cls()
    return Agent(
        name="technical_analyzer_agent",
        model="gemini-2.0-flash",
        description="Analyzes technical and financial numeric indicators from web evidence.",
        instruction=(
            "You are the Technical Analyzer. Extract technical/financial metrics (sales, market cap, "
            "earnings, growth indicators) and explain trends and caveats. "
            "If values are missing/unreliable, state that clearly."
        ),
        tools=[search_web, get_general_overview, build_company_report],
    )


# # FUNCTION: create_technical_researcher_agent
# Purpose: build an agent that synthesizes deep technical research insights from numeric context.
def create_technical_researcher_agent():
    """Create the Technical Researcher Agent.

    Capabilities:
    - Performs deeper interpretation over technical/financial findings.
    - Produces insight-oriented narratives and actionable observations.
    - Connects business context with metric behavior.
    """

    Agent = _agent_cls()
    return Agent(
        name="technical_researcher_agent",
        model="gemini-2.0-flash",
        description="Conducts deeper technical research and insight synthesis over company metrics.",
        instruction=(
            "You are the Technical Researcher. Use technical evidence to produce high-signal insights, "
            "opportunities, concerns, and what-to-watch points. Keep reasoning auditable with sources."
        ),
        tools=[search_web, build_company_report],
    )


# # FUNCTION: create_dcf_helper_agent
# Purpose: build a helper agent that explains DCF inputs and ways to estimate missing variables.
def create_dcf_helper_agent():
    """Create the DCF Helper Agent.

    Capabilities:
    - Explains required DCF variables and formulas.
    - Suggests methods to estimate missing variables responsibly.
    - Provides assumption templates and sanity checks.
    """

    Agent = _agent_cls()
    return Agent(
        name="dcf_helper_agent",
        model="gemini-2.0-flash",
        description="Explains DCF methodology, required variables, and missing-variable estimation methods.",
        instruction=(
            "You are the DCF Helper. List required DCF variables (FCF, growth, discount rate, terminal value, "
            "horizon, debt/cash, shares outstanding), explain estimation approaches, and document assumptions."
        ),
        tools=[search_web],
    )


# # FUNCTION: create_dcf_analyzer_agent
# Purpose: build an agent that performs DCF-oriented analysis using technical evidence + helper logic.
def create_dcf_analyzer_agent():
    """Create the DCF Analyzer Agent.

    Capabilities:
    - Performs DCF-style analytical framing from available data.
    - Coordinates with DCF helper guidance on missing variables.
    - Produces scenario-based valuation narratives (base/bull/bear assumptions).
    """

    Agent = _agent_cls()
    return Agent(
        name="dcf_analyzer_agent",
        model="gemini-2.0-flash",
        description="Performs DCF-oriented valuation reasoning with assumptions and scenarios.",
        instruction=(
            "You are the DCF Analyzer. Build a transparent DCF-style assessment from available evidence. "
            "Show assumptions, ranges, and sensitivity. Mention missing data and dependency on DCF Helper logic."
        ),
        tools=[search_web, build_company_report],
    )


# # FUNCTION: create_master_agent
# Purpose: build orchestration agent that coordinates all specialist roles.
def create_master_agent():
    """Create the Master Agent (orchestrator).

    Capabilities:
    - Accepts user requests and orchestrates specialist-agent viewpoints.
    - Delegates to role-aligned tools and combines findings.
    - Returns integrated report with clear section ownership.
    """

    Agent = _agent_cls()
    return Agent(
        name="master_agent",
        model="gemini-2.0-flash",
        description="Orchestrates Research, News, Semantic, Technical, and DCF perspectives.",
        instruction=(
            "You are the Master Agent orchestrator. Coordinate across these specialist roles: "
            "Research Agent, News Agent, Semantic Agent, Technical Analyzer, Technical Researcher, "
            "DCF Analyzer, and DCF Helper. For each user request, produce a structured multi-section response "
            "covering: company profile, news/projects, semantic sentiment + promise-vs-delivery, "
            "technical numbers and analysis, and DCF framing. Mention evidence gaps and source links."
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


# # FUNCTION: create_agent_catalog
# Purpose: return a dictionary of all specialized agent factory callables for orchestration/reference.
def create_agent_catalog():
    """Return mapping of all requested agent factories."""

    return {
        "research_agent": create_research_agent,
        "news_agent": create_news_agent,
        "semantic_agent": create_semantic_agent,
        "technical_analyzer_agent": create_technical_analyzer_agent,
        "technical_researcher_agent": create_technical_researcher_agent,
        "dcf_helper_agent": create_dcf_helper_agent,
        "dcf_analyzer_agent": create_dcf_analyzer_agent,
        "master_agent": create_master_agent,
    }
