"""Integration tests for the LangGraph workflow with mocked retrieval."""

import pytest

from linkedin_intelligence.graph.builder import graph
from linkedin_intelligence.models.state import IntelligenceState


@pytest.mark.asyncio
async def test_full_graph_execution_mocked():
    initial_state: IntelligenceState = {
        "request_id": "test-req-001",
        "user_request": "Find companies hiring backend engineers in India with CTO involvement.",
        "raw_results": [],
        "normalized_posts": [],
        "signals": [],
        "companies": [],
        "contacts": [],
        "opportunities": [],
        "selected_opportunity_ids": [],
        "errors": [],
        "warnings": [],
        "metrics": {},
        "agent_events": [],
    }

    result = await graph.ainvoke(initial_state)

    # Verify state updates
    assert "intent" in result
    assert result["intent"].signal_type == "hiring"
    assert "backend engineer" in result["intent"].target_roles

    assert "search_plan" in result
    assert len(result["search_plan"].queries) > 0

    assert "normalized_posts" in result
    assert len(result["normalized_posts"]) > 0

    assert "signals" in result
    assert len(result["signals"]) > 0

    assert "opportunities" in result
    assert len(result["opportunities"]) > 0

    # Verify top opportunity properties
    top_opp = result["opportunities"][0]
    assert top_opp.score > 0
    assert top_opp.temperature in ["HOT", "WARM", "LOW"]
    assert len(top_opp.why_detected) > 0
    assert len(top_opp.recommended_action) > 0

    # Verify agent events
    events = result["agent_events"]
    nodes_executed = [e["node"] for e in events]
    assert "Intent Agent" in nodes_executed
    assert "Query Expansion Agent" in nodes_executed
    assert "Retrieval Agent" in nodes_executed
    assert "Opportunity Agent" in nodes_executed


@pytest.mark.asyncio
async def test_graph_empty_request_behavior():
    initial_state: IntelligenceState = {
        "request_id": "test-req-empty",
        "user_request": "",
        "raw_results": [],
        "normalized_posts": [],
        "signals": [],
        "companies": [],
        "contacts": [],
        "opportunities": [],
        "selected_opportunity_ids": [],
        "errors": [],
        "warnings": [],
        "metrics": {},
        "agent_events": [],
    }

    result = await graph.ainvoke(initial_state)
    assert "intent" in result
    assert "opportunities" in result
