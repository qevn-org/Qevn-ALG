"""Intent Agent: extracts structured SearchIntent from user natural language request."""

from datetime import datetime, timezone

import structlog

from linkedin_intelligence.agents.llm_helper import run_structured_llm
from linkedin_intelligence.models.search import SearchIntent
from linkedin_intelligence.models.state import AgentEvent, IntelligenceState

logger = structlog.get_logger(__name__)


def _extract_intent_rule_based(user_request: str) -> SearchIntent:
    """Deterministic fallback for parsing intent without LLM."""
    req_lower = user_request.lower()

    # Extract roles
    target_roles = []
    for r in ["backend engineer", "software engineer", "platform engineer", "full stack developer", "data architect", "ml engineer"]:
        if r in req_lower:
            target_roles.append(r)
    if not target_roles:
        target_roles = ["backend engineer", "software engineer"]

    # Extract geographies
    geographies = []
    for loc in ["india", "bangalore", "bengaluru", "delhi", "gurgaon", "noida", "mumbai", "pune", "hyderabad", "remote"]:
        if loc in req_lower:
            geographies.append(loc.title())
    if not geographies and "india" in req_lower:
        geographies = ["India"]

    # Extract stakeholders
    decision_makers = []
    for dm in ["cto", "founder", "co-founder", "vp engineering", "head of talent", "vp", "engineering director"]:
        if dm in req_lower:
            decision_makers.append(dm.upper() if len(dm) <= 3 else dm.title())
    if not decision_makers:
        decision_makers = ["CTO", "Founder", "VP Engineering", "Head of Talent"]

    # Freshness
    freshness = 7
    if "14" in req_lower or "2 weeks" in req_lower:
        freshness = 14
    elif "30" in req_lower or "month" in req_lower:
        freshness = 30
    elif "3 days" in req_lower or "24 hours" in req_lower:
        freshness = 3

    return SearchIntent(
        objective=f"Discover hiring opportunities for {', '.join(target_roles)} in {', '.join(geographies) or 'India'}",
        signal_type="hiring",
        target_roles=target_roles,
        target_industries=[],
        geographies=geographies or ["India"],
        target_company_sizes=[],
        target_seniority=["senior", "lead"],
        freshness_days=freshness,
        decision_maker_types=decision_makers,
        required_terms=[],
        excluded_terms=[],
    )


async def intent_node(state: IntelligenceState) -> dict:
    """LangGraph node for Intent Agent."""
    user_request = state.get("user_request", "")
    logger.info("intent_agent_started", request=user_request[:80])

    fallback_intent = _extract_intent_rule_based(user_request)

    structured_data = await run_structured_llm(
        prompt_file="intent.txt",
        user_content=f"User request:\n{user_request}",
        default_fallback=fallback_intent.model_dump(),
    )

    try:
        intent = SearchIntent(**structured_data)
    except Exception as e:
        logger.warning("intent_validation_failed_using_fallback", error=str(e))
        intent = fallback_intent

    event = AgentEvent(
        node="Intent Agent",
        status="completed",
        summary=f"Parsed objective: {intent.objective}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={"target_roles": intent.target_roles, "geographies": intent.geographies},
    )

    existing_events = list(state.get("agent_events", []))
    existing_events.append(event.model_dump())

    logger.info("intent_agent_completed", objective=intent.objective)
    return {
        "intent": intent,
        "agent_events": existing_events,
    }
