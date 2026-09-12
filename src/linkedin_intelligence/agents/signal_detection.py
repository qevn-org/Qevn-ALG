"""Signal Detection Agent: identifies structured hiring and growth signals with evidence citations."""

from datetime import datetime, timezone
from typing import Any

import structlog

from linkedin_intelligence.agents.llm_helper import run_structured_llm
from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.models.signals import Signal, SignalType
from linkedin_intelligence.models.state import AgentEvent, IntelligenceState

logger = structlog.get_logger(__name__)


def _detect_signals_heuristic(
    posts: list[LinkedInPost], intent: Any | None = None
) -> list[Signal]:
    """Deterministic heuristic signal extraction with dynamic role and company handling."""
    signals: list[Signal] = []

    # Target roles from intent
    target_roles = []
    if intent and getattr(intent, "target_roles", None):
        target_roles = [r.strip().lower() for r in intent.target_roles if r.strip()]

    # Group by company / practice
    company_posts: dict[str, list[LinkedInPost]] = {}
    for p in posts:
        comp = p.company_name
        if not comp or comp.lower() in ("unknown company", "org", "practice"):
            if p.author_name:
                comp = f"{p.author_name}'s Practice / Team"
            else:
                comp = "Healthcare & Clinic Group"
        company_posts.setdefault(comp, []).append(p)

    hiring_keywords = [
        "hiring", "looking for", "join our team", "we are expanding",
        "open roles", "careers", "apply", "opportunity", "seeking", "vacancy", "vacancies"
    ]
    urgency_keywords = ["urgent", "urgently", "immediate", "immediately", "immediate joiners", "fast-track"]

    for comp, comp_p_list in company_posts.items():
        evidence_ids = []
        roles_detected = set()
        locations_detected = set()
        dms_detected = set()
        is_urgent = False
        is_acceleration = len(comp_p_list) > 1

        for p in comp_p_list:
            text_lower = p.content.lower()
            if any(k in text_lower for k in hiring_keywords) or len(comp_p_list) == 1:
                evidence_ids.append(p.id)

                if any(u in text_lower for u in urgency_keywords):
                    is_urgent = True

                # 1. Match from intent target roles
                for tr in target_roles:
                    if tr in text_lower:
                        roles_detected.add(tr.title())

                # 2. Match general domains
                for role in [
                    "dentist", "associate dentist", "dental surgeon", "orthodontist", "dental hygienist",
                    "doctor", "physician", "backend engineer", "software engineer", "platform engineer",
                    "data architect", "ml engineer", "full stack developer"
                ]:
                    if role in text_lower:
                        roles_detected.add(role.title())

                # Locations
                for loc in [
                    "bangalore", "delhi", "gurgaon", "noida", "mumbai", "pune", "hyderabad",
                    "india", "australia", "victoria", "sunshine coast", "london", "uk", "remote"
                ]:
                    if loc in text_lower:
                        locations_detected.add(loc.title())

                # Stakeholders
                if p.author_name:
                    dms_detected.add(f"{p.author_name} ({p.author_headline or 'Hiring Contact'})")

        if evidence_ids:
            sig_type = SignalType.HIRING
            if is_urgent:
                sig_type = SignalType.URGENT_HIRING
            elif is_acceleration:
                sig_type = SignalType.HIRING_ACCELERATION

            final_roles = list(roles_detected)
            if not final_roles and target_roles:
                final_roles = [r.title() for r in target_roles]
            if not final_roles:
                final_roles = ["Professional Specialist"]

            confidence = 0.90 if len(evidence_ids) > 1 or dms_detected else 0.82
            urgency_score = 0.85 if is_urgent else 0.70

            explanation = (
                f"{comp} exhibits active {sig_type.value.lower().replace('_', ' ')} for {final_roles} "
                f"evidenced in {len(evidence_ids)} post(s)."
            )

            signals.append(
                Signal(
                    signal_type=sig_type.value,
                    company_name=comp,
                    confidence=confidence,
                    urgency=urgency_score,
                    evidence_post_ids=evidence_ids,
                    detected_roles=final_roles,
                    detected_locations=list(locations_detected) or ["Active Location"],
                    detected_decision_makers=list(dms_detected),
                    explanation=explanation,
                )
            )

    return signals


async def signal_detection_node(state: IntelligenceState) -> dict:
    """LangGraph node for Signal Detection Agent."""
    posts: list[LinkedInPost] = state.get("normalized_posts", [])
    logger.info("signal_detection_started", posts_count=len(posts))

    if not posts:
        event = AgentEvent(
            node="Signal Detection Agent",
            status="completed",
            summary="No posts available for signal detection",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        existing_events = list(state.get("agent_events", []))
        existing_events.append(event.model_dump())
        return {"signals": [], "agent_events": existing_events}

    fallback_signals = _detect_signals_heuristic(posts, intent=state.get("intent"))

    # Format posts for LLM prompt
    posts_payload = [
        {
            "id": p.id,
            "company": p.company_name,
            "author": p.author_name,
            "headline": p.author_headline,
            "text": p.content_preview,
        }
        for p in posts[:10]
    ]

    structured_data = await run_structured_llm(
        prompt_file="signal_detection.txt",
        user_content=f"Normalized LinkedIn posts to analyze:\n{posts_payload}",
        default_fallback=[s.model_dump() for s in fallback_signals],
    )

    signals: list[Signal] = []
    if isinstance(structured_data, list):
        for item in structured_data:
            try:
                signals.append(Signal(**item))
            except Exception:
                continue

    if not signals:
        signals = fallback_signals

    event = AgentEvent(
        node="Signal Detection Agent",
        status="completed",
        summary=f"Detected {len(signals)} evidence-backed commercial hiring signals",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={"signals_count": len(signals)},
    )

    existing_events = list(state.get("agent_events", []))
    existing_events.append(event.model_dump())

    metrics = dict(state.get("metrics", {}))
    metrics["signals_count"] = len(signals)

    logger.info("signal_detection_completed", signals_count=len(signals))
    return {
        "signals": signals,
        "metrics": metrics,
        "agent_events": existing_events,
    }
