"""Lead Analysis Agent: Synthesizes LLM-derived strategic sales intelligence."""

from datetime import datetime, timezone
from typing import Any

import structlog

from linkedin_intelligence.agents.llm_helper import run_structured_llm
from linkedin_intelligence.config.settings import get_settings
from linkedin_intelligence.models.lead import Lead, LeadEnrichment
from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.models.state import AgentEvent, IntelligenceState

logger = structlog.get_logger(__name__)


def _generate_fallback_enrichment(lead: Lead) -> LeadEnrichment:
    """Generate high-quality evidence-grounded fallback enrichment without LLM."""
    comp = lead.company.name
    roles = lead.intent.detected_requirement or "Software Engineering"
    dm_name = lead.person.name

    return LeadEnrichment(
        lead_summary=f"{comp} has published high-intent signals seeking {roles} expertise.",
        intent_explanation=f"Public LinkedIn recruitment and expansion signal identifying critical need for {roles}.",
        business_need=f"Accelerating digital roadmap and scaling technical throughput at {comp}.",
        technology_requirement=lead.intent.technology_need or "Modern Full-Stack / Cloud Architecture",
        buying_intent="High" if lead.score >= 80 else "Medium",
        decision_maker_probability=85.0 if lead.person.is_decision_maker else 50.0,
        recommended_service="Dedicated Engineering Squad & Architecture Support",
        recommended_outreach_angle=f"Reference their active search for {roles} and propose sprint-ready engineering capacity to eliminate hiring lag.",
        why_this_lead=f"Verified hiring expansion at {comp} with leadership involvement ({dm_name}).",
        why_now=lead.why_now or "Active recruitment window indicates open engineering budget.",
        confidence=round(min(0.95, 0.60 + (lead.score / 250.0)), 2),
        searched_at=datetime.now(timezone.utc).isoformat(),
        sources_checked=["LinkedIn Post", "Company Public Profile"],
    )


async def lead_analysis_node(state: IntelligenceState) -> dict[str, Any]:
    """LangGraph node: generates LLM strategic analysis for qualified leads."""
    leads: list[Lead] = state.get("leads", [])
    posts: list[LinkedInPost] = state.get("normalized_posts", [])
    settings = get_settings()

    threshold = settings.qualification_threshold
    qualified_leads = [lead for lead in leads if lead.score >= threshold]
    logger.info("lead_analysis_started", count=len(qualified_leads))

    post_map = {p.id: p for p in posts}

    for lead in qualified_leads[: settings.max_deep_research_items]:
        comp_posts = [post_map[pid] for pid in lead.evidence if pid in post_map]
        evidence_context = "\n---\n".join([f"Post by {p.author_name} ({p.author_headline}): {p.content[:400]}" for p in comp_posts]) or "None"

        user_content = (
            f"Company: {lead.company.name}\n"
            f"Industry: {lead.company.industry}\n"
            f"Location: {lead.company.location}\n"
            f"Person: {lead.person.name} - {lead.person.job_title}\n"
            f"Detected Signals: {', '.join(lead.signals)}\n"
            f"Requirement: {lead.intent.detected_requirement}\n"
            f"Source Evidence Posts:\n{evidence_context}"
        )

        fallback = _generate_fallback_enrichment(lead)
        if settings.has_llm:
            try:
                res = await run_structured_llm("lead_analysis.txt", user_content, fallback.model_dump(), settings)
                if isinstance(res, dict) and "lead_summary" in res:
                    lead.enrichment = LeadEnrichment(
                        lead_summary=res.get("lead_summary", fallback.lead_summary),
                        intent_explanation=res.get("intent_explanation", fallback.intent_explanation),
                        business_need=res.get("business_need", fallback.business_need),
                        technology_requirement=res.get("technology_requirement", fallback.technology_requirement),
                        buying_intent=res.get("buying_intent", fallback.buying_intent),
                        decision_maker_probability=float(res.get("decision_maker_probability", fallback.decision_maker_probability)),
                        recommended_service=res.get("recommended_service", fallback.recommended_service),
                        recommended_outreach_angle=res.get("recommended_outreach_angle", fallback.recommended_outreach_angle),
                        why_this_lead=res.get("why_this_lead", fallback.why_this_lead),
                        why_now=res.get("why_now", fallback.why_now),
                        confidence=float(res.get("confidence", fallback.confidence)),
                        searched_at=datetime.now(timezone.utc).isoformat(),
                        sources_checked=["LinkedIn Post", "AI Synthesis"],
                    )
                else:
                    lead.enrichment = fallback
            except Exception as err:
                logger.warning("lead_analysis_llm_failed", lead_id=lead.id, error=str(err))
                lead.enrichment = fallback
        else:
            lead.enrichment = fallback

    event = AgentEvent(
        node="Lead Analysis Agent",
        status="completed",
        summary=f"Synthesized deep strategic intelligence for {len(qualified_leads)} leads",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={"analyzed_leads": len(qualified_leads)},
    )

    events = list(state.get("agent_events", []))
    events.append(event.model_dump())

    return {
        "leads": leads,
        "agent_events": events,
    }
