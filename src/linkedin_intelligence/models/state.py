"""Typed LangGraph state definition for the intelligence workflow."""

from typing import Any, TypedDict

from pydantic import BaseModel, Field

from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.models.opportunities import Opportunity
from linkedin_intelligence.models.search import SearchIntent, SearchPlan
from linkedin_intelligence.models.signals import Signal


class AgentEvent(BaseModel):
    """Structured event emitted when an agent node executes."""

    node: str = Field(..., description="Name of the node or agent")
    status: str = Field(..., description="running, completed, failed, skipped")
    summary: str = Field(..., description="User-readable description of current step")
    timestamp: str = Field(..., description="ISO timestamp")
    data: dict[str, Any] = Field(default_factory=dict, description="Metadata associated with event")


class IntelligenceState(TypedDict, total=False):
    """Central typed state passed through the LangGraph workflow."""

    request_id: str
    user_request: str

    intent: SearchIntent
    search_plan: SearchPlan

    raw_results: list[dict[str, Any]]
    normalized_posts: list[LinkedInPost]
    signals: list[Signal]

    companies: list[dict[str, Any]]
    contacts: list[dict[str, Any]]

    opportunities: list[Opportunity]
    selected_opportunity_ids: list[str]
    leads: list[Any]

    errors: list[str]
    warnings: list[str]

    metrics: dict[str, Any]
    agent_events: list[dict[str, Any]]
