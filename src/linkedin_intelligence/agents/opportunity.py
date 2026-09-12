"""Opportunity Agent: transforms qualified evidence into structured executive opportunities."""

from datetime import datetime, timezone

import structlog

from linkedin_intelligence.models.opportunities import Opportunity
from linkedin_intelligence.models.state import AgentEvent, IntelligenceState

logger = structlog.get_logger(__name__)


async def opportunity_node(state: IntelligenceState) -> dict:
    """Finalize executive opportunity synthesis."""
    opportunities: list[Opportunity] = state.get("opportunities", [])

    logger.info("opportunity_agent_started", total_opps=len(opportunities))

    for opp in opportunities:
        # Polish why_detected and recommended action
        roles_str = ", ".join(opp.detected_roles[:3]) or "engineering roles"

        # Evidence bullet points
        why_bullets = []
        if opp.evidence_post_ids:
            why_bullets.append(f"{len(opp.evidence_post_ids)} active LinkedIn post(s) advertising {roles_str}.")

        if opp.contacts:
            lead_names = [f"{c.name} ({c.role_type})" for c in opp.contacts[:2]]
            why_bullets.append(f"Involvement of key leadership: {', '.join(lead_names)}.")

        if opp.urgency >= 75.0:
            why_bullets.append("Urgent hiring timeline / immediate joiner preference specified.")

        opp.why_detected = why_bullets or [f"Hiring activity detected for {roles_str}"]

        # Recommended Action
        if opp.contacts:
            top_c = opp.contacts[0]
            opp.recommended_action = (
                f"Contact {top_c.name} ({top_c.role_type}) referencing their recent post seeking {roles_str} "
                f"to offer targeted talent support."
            )
        else:
            opp.recommended_action = (
                f"Research engineering leadership at {opp.company_name} and initiate candidate matching for {roles_str}."
            )

    hot_count = sum(1 for o in opportunities if o.temperature == "HOT")
    warm_count = sum(1 for o in opportunities if o.temperature == "WARM")
    low_count = sum(1 for o in opportunities if o.temperature == "LOW")

    event = AgentEvent(
        node="Opportunity Agent",
        status="completed",
        summary=f"Finalized {len(opportunities)} opportunities ({hot_count} HOT, {warm_count} WARM, {low_count} LOW)",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={"hot": hot_count, "warm": warm_count, "low": low_count},
    )

    existing_events = list(state.get("agent_events", []))
    existing_events.append(event.model_dump())

    metrics = dict(state.get("metrics", {}))
    metrics["hot_count"] = hot_count
    metrics["warm_count"] = warm_count
    metrics["low_count"] = low_count

    logger.info(
        "opportunity_agent_completed",
        total=len(opportunities),
        hot=hot_count,
        warm=warm_count,
        low=low_count,
    )

    from linkedin_intelligence.db.repository import get_lead_repository
    from linkedin_intelligence.models.lead import SearchRunRecord

    repo = get_lead_repository()
    leads = state.get("leads", [])
    if leads:
        repo.upsert_leads(leads)

    # Record search run
    req_id = state.get("request_id", "manual_run")
    user_req = state.get("user_request", "Discovery Query")
    run_record = SearchRunRecord(
        run_id=req_id,
        user_query=user_req,
        start_time=datetime.now(timezone.utc).isoformat(),
        end_time=datetime.now(timezone.utc).isoformat(),
        result_count=len(state.get("raw_results", [])),
        normalized_count=len(state.get("normalized_posts", [])),
        duplicate_count=len(state.get("raw_results", [])) - len(state.get("normalized_posts", [])),
        signal_count=len(state.get("signals", [])),
        qualified_count=len(opportunities),
        enriched_count=len(leads),
        error_count=len(state.get("errors", [])),
    )
    repo.save_search_run(run_record)

    return {
        "opportunities": opportunities,
        "leads": leads,
        "metrics": metrics,
        "agent_events": existing_events,
    }

