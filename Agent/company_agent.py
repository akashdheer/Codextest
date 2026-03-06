"""Backward-compatible root agent factory.

This module keeps the old `create_root_agent` name while routing to the new
Master Agent orchestrator.
"""

from __future__ import annotations

from Agent.multi_agents import create_master_agent


# # FUNCTION: create_root_agent
# Purpose: preserve existing imports while returning the new Master Agent.
def create_root_agent():
    """Create and return the Master Agent orchestrator (backward-compatible alias)."""

    return create_master_agent()
