"""Query Expansion Agent: generates structured query families from SearchIntent."""

from datetime import datetime, timezone

import structlog

from linkedin_intelligence.agents.llm_helper import run_structured_llm
from linkedin_intelligence.config.settings import get_settings
from linkedin_intelligence.models.search import SearchIntent, SearchPlan
from linkedin_intelligence.models.state import AgentEvent, IntelligenceState

logger = structlog.get_logger(__name__)


def _generate_queries_rule_based(intent: SearchIntent) -> SearchPlan:
    """Deterministic generation of query families."""
    roles = intent.target_roles or ["backend engineer", "software engineer"]
    geos = intent.geographies or ["India"]
    primary_geo = geos[0] if geos else "India"

    families: list[str] = []

    for role in roles:
        # 1. Direct hiring
        families.append(f"hiring {role}")
        families.append(f"we are hiring {role}")
        families.append(f"hiring {role} {primary_geo}")

        # 2. Team growth
        families.append(f"growing engineering team {role}")
        families.append(f"expanding our engineering team {role}")

        # 3. Urgency
        families.append(f"urgent hiring {role}")
        families.append(f"immediate hiring {role}")

        # 4. Leadership / DM hiring
        families.append(f"DM me {role}")
        families.append(f"CTO hiring {role}")
        families.append(f"VP Engineering hiring {role}")

    # Deduplicate preserving order
    seen = set()
    deduped_queries = []
    for q in families:
        q_norm = " ".join(q.lower().split())
        if q_norm not in seen:
            seen.add(q_norm)
            deduped_queries.append(q)

    max_q = get_settings().max_search_queries
    final_queries = deduped_queries[:max_q]

    return SearchPlan(
        queries=final_queries,
        company_identifiers=[],
        max_queries=max_q,
        rationale=f"Generated {len(final_queries)} query variants covering direct hiring, team growth, urgency, and leadership language.",
    )


async def query_expansion_node(state: IntelligenceState) -> dict:
    """LangGraph node for Query Expansion Agent."""
    intent: SearchIntent = state.get("intent")  # type: ignore[assignment]
    if not intent:
        intent = SearchIntent(objective="Find engineering hiring signals")

    logger.info("query_expansion_started", roles=intent.target_roles)
    fallback_plan = _generate_queries_rule_based(intent)

    structured_data = await run_structured_llm(
        prompt_file="query_expansion.txt",
        user_content=f"Search Intent:\n{intent.model_dump_json(indent=2)}",
        default_fallback=fallback_plan.model_dump(),
    )

    try:
        plan = SearchPlan(**structured_data)
        # Ensure non-empty queries and enforce max limit
        if not plan.queries:
            plan = fallback_plan
        max_q = get_settings().max_search_queries
        plan.queries = plan.queries[:max_q]
    except Exception as e:
        logger.warning("query_expansion_validation_failed", error=str(e))
        plan = fallback_plan

    event = AgentEvent(
        node="Query Expansion Agent",
        status="completed",
        summary=f"Generated {len(plan.queries)} queries across direct hiring, expansion, and urgency",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={"query_count": len(plan.queries), "queries": plan.queries[:5]},
    )

    existing_events = list(state.get("agent_events", []))
    existing_events.append(event.model_dump())

    logger.info("query_expansion_completed", queries_count=len(plan.queries))
    return {
        "search_plan": plan,
        "agent_events": existing_events,
    }
