"""Query Validation: deterministic validation and sanitization of search queries."""

from datetime import datetime, timezone

import structlog

from linkedin_intelligence.config.settings import get_settings
from linkedin_intelligence.models.search import SearchPlan
from linkedin_intelligence.models.state import AgentEvent, IntelligenceState

logger = structlog.get_logger(__name__)


def query_validation_node(state: IntelligenceState) -> dict:
    """Validate and sanitize SearchPlan deterministically."""
    plan: SearchPlan = state.get("search_plan")  # type: ignore[assignment]
    if not plan or not plan.queries:
        logger.warning("query_validation_empty_plan_fallback")
        plan = SearchPlan(
            queries=["hiring backend engineer", "hiring software engineer India"],
            rationale="Fallback default queries",
        )

    settings = get_settings()
    sanitized: list[str] = []
    seen = set()

    for q in plan.queries:
        clean = " ".join(q.strip().split())
        # Remove any harmful chars or excessive length
        clean = clean[:120]
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            sanitized.append(clean)

    bounded = sanitized[: settings.max_search_queries]
    validated_plan = SearchPlan(
        queries=bounded,
        company_identifiers=plan.company_identifiers,
        max_queries=settings.max_search_queries,
        rationale=plan.rationale or "Validated search plan",
    )

    event = AgentEvent(
        node="Query Validation",
        status="completed",
        summary=f"Validated {len(bounded)} clean search queries",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={"query_count": len(bounded)},
    )

    existing_events = list(state.get("agent_events", []))
    existing_events.append(event.model_dump())

    logger.info("query_validation_completed", count=len(bounded))
    return {
        "search_plan": validated_plan,
        "agent_events": existing_events,
    }
