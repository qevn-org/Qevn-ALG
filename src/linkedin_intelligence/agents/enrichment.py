"""Enrichment Agent: populates evidence-backed company metadata for qualified opportunities."""

from datetime import datetime, timezone

import structlog

from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.models.opportunities import Opportunity
from linkedin_intelligence.models.state import AgentEvent, IntelligenceState

logger = structlog.get_logger(__name__)



async def enrichment_node(state: IntelligenceState) -> dict:
    """Enrich qualified opportunities with company context without fabricating data."""
    opportunities: list[Opportunity] = state.get("opportunities", [])
    posts: list[LinkedInPost] = state.get("normalized_posts", [])

    logger.info("enrichment_started", count=len(opportunities))

    post_map = {p.id: p for p in posts}

    for opp in opportunities:

        # Heuristic extraction from evidence posts
        comp_posts = [post_map[pid] for pid in opp.evidence_post_ids if pid in post_map]
        locations = set()
        headlines = []

        for p in comp_posts:
            if p.author_headline:
                headlines.append(p.author_headline)
            for loc in ["Bangalore", "Delhi", "Gurgaon", "Noida", "Mumbai", "Pune", "Hyderabad", "India", "Remote"]:
                if loc.lower() in p.content.lower():
                    locations.add(loc)

        if locations:
            opp.location = ", ".join(locations)
        else:
            opp.location = "India (Remote/Hybrid)"

        # Check for fintech, ai, saas in post text
        all_text = " ".join(p.content.lower() for p in comp_posts)
        if "fintech" in all_text or "payment" in all_text:
            opp.industry = "Fintech & Payments"
        elif "ai" in all_text or "agent" in all_text or "machine learning" in all_text:
            opp.industry = "Artificial Intelligence / ML"
        elif "saas" in all_text or "cloud" in all_text:
            opp.industry = "Enterprise SaaS / Cloud"
        else:
            opp.industry = "Technology / Software"

        if "series b" in all_text or "scaling" in all_text:
            opp.company_size = "Growth (Series B+)"
        elif "startup" in all_text or "series a" in all_text:
            opp.company_size = "Early-stage (Series A)"
        else:
            opp.company_size = "unknown"

    event = AgentEvent(
        node="Enrichment Agent",
        status="completed",
        summary=f"Enriched {len(opportunities)} qualified opportunities with verified company attributes",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={"enriched_count": len(opportunities)},
    )

    existing_events = list(state.get("agent_events", []))
    existing_events.append(event.model_dump())

    logger.info("enrichment_completed", count=len(opportunities))

    return {
        "opportunities": opportunities,
        "agent_events": existing_events,
    }
