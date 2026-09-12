"""Retrieval Agent: invokes LinkedInRetrievalService to search LinkedIn posts."""

import time
from datetime import datetime, timezone

import structlog

from linkedin_intelligence.models.search import SearchPlan
from linkedin_intelligence.models.state import AgentEvent, IntelligenceState
from linkedin_intelligence.tools.retrieval_service import LinkedInRetrievalService

logger = structlog.get_logger(__name__)


async def retrieval_node(state: IntelligenceState) -> dict:
    """LangGraph node executing search plan via LinkedInRetrievalService."""
    plan: SearchPlan = state.get("search_plan")  # type: ignore[assignment]
    if not plan:
        logger.error("retrieval_missing_search_plan")
        return {"raw_results": [], "errors": ["Missing search plan in state"]}

    t0 = time.time()
    service = LinkedInRetrievalService()

    try:
        raw_results = await service.search(plan)
        duration_ms = round((time.time() - t0) * 1000, 1)

        event = AgentEvent(
            node="Retrieval Agent",
            status="completed",
            summary=f"Retrieved {len(raw_results)} public LinkedIn posts in {duration_ms}ms",
            timestamp=datetime.now(timezone.utc).isoformat(),
            data={"count": len(raw_results), "duration_ms": duration_ms},
        )

        existing_events = list(state.get("agent_events", []))
        existing_events.append(event.model_dump())

        metrics = dict(state.get("metrics", {}))
        metrics["retrieval_count"] = len(raw_results)
        metrics["retrieval_duration_ms"] = duration_ms

        logger.info("retrieval_node_completed", count=len(raw_results), duration_ms=duration_ms)
        return {
            "raw_results": raw_results,
            "metrics": metrics,
            "agent_events": existing_events,
        }
    except Exception as e:
        logger.error("retrieval_node_error", error=str(e))
        event = AgentEvent(
            node="Retrieval Agent",
            status="failed",
            summary=f"Retrieval failed: {str(e)}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            data={"error": str(e)},
        )
        existing_events = list(state.get("agent_events", []))
        existing_events.append(event.model_dump())

        errors = list(state.get("errors", []))
        errors.append(f"Retrieval error: {str(e)}")

        return {
            "raw_results": [],
            "errors": errors,
            "agent_events": existing_events,
        }
