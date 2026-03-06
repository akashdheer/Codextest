"""Backward-compatible entrypoint for the company overview agent modules."""

from __future__ import annotations

import json

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


if __name__ == "__main__":
    import sys

    arg = " ".join(sys.argv[1:]).strip()
    if arg == "--check-api":
        print(json.dumps(check_search_api_credentials(), indent=2, default=str))
    else:
        company = arg or "Microsoft"
        print(json.dumps(build_company_report(company), indent=2, default=str))
