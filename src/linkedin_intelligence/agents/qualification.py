"""Qualification Agent: evaluates commercial relevance and invokes deterministic scoring."""

from datetime import datetime, timezone

import structlog

from linkedin_intelligence.agents.llm_helper import run_structured_llm
from linkedin_intelligence.config.settings import get_settings
from linkedin_intelligence.models.opportunities import Opportunity
from linkedin_intelligence.models.search import SearchIntent
from linkedin_intelligence.models.signals import Signal
from linkedin_intelligence.models.state import AgentEvent, IntelligenceState
from linkedin_intelligence.services.scoring import calculate_opportunity_score

logger = structlog.get_logger(__name__)


def _evaluate_heuristic(
    signal: Signal, intent: SearchIntent | None
) -> dict:
    """Heuristic scoring evaluation for fallback."""
    # Hiring Intent: based on signal type and evidence count
    hiring_intent = 90.0 if "ACCELERATION" in signal.signal_type or "EXPANSION" in signal.signal_type else 80.0

    # Decision Maker: 90 if DM detected, else 55
    decision_maker = 90.0 if signal.detected_decision_makers else 55.0

    # Company Fit: role alignment
    company_fit = 85.0
    if intent and intent.target_roles:
        matches = any(
            any(tr.lower() in dr.lower() for dr in signal.detected_roles)
            for tr in intent.target_roles
        )
        company_fit = 95.0 if matches else 70.0

    # Freshness
    freshness = 90.0

    # Urgency
    urgency = round(signal.urgency * 100, 1)

    # Evidence Confidence
    evidence_conf = round(signal.confidence * 100, 1)

    return {
        "company_name": signal.company_name,
        "hiring_intent": hiring_intent,
        "decision_maker": decision_maker,
        "company_fit": company_fit,
        "freshness": freshness,
        "urgency": urgency,
        "evidence_confidence": evidence_conf,
        "detected_roles": signal.detected_roles,
        "evidence_post_ids": signal.evidence_post_ids,
        "why_now": f"Active hiring momentum detected in {signal.detected_locations or ['India']}.",
    }


async def qualification_node(state: IntelligenceState) -> dict:
    """LangGraph node assessing qualification and computing deterministic scores."""
    signals: list[Signal] = state.get("signals", [])
    intent: SearchIntent = state.get("intent")  # type: ignore[assignment]
    settings = get_settings()

    logger.info("qualification_started", signals_count=len(signals))

    if not signals:
        event = AgentEvent(
            node="Qualification Agent",
            status="completed",
            summary="No signals to qualify",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        existing_events = list(state.get("agent_events", []))
        existing_events.append(event.model_dump())
        return {"opportunities": [], "agent_events": existing_events}

    # Group signals by company
    company_signals: dict[str, list[Signal]] = {}
    for s in signals:
        if s.company_name:
            company_signals.setdefault(s.company_name, []).append(s)

    candidate_evals = []
    for comp, sigs in company_signals.items():
        primary_sig = sigs[0]
        # Merge roles & evidence across company signals
        all_roles = list({r for s in sigs for r in s.detected_roles})
        all_ids = list({pid for s in sigs for pid in s.evidence_post_ids})
        primary_sig.detected_roles = all_roles
        primary_sig.evidence_post_ids = all_ids
        eval_item = _evaluate_heuristic(primary_sig, intent)
        candidate_evals.append(eval_item)

    # Optional LLM refinement
    structured_data = await run_structured_llm(
        prompt_file="qualification.txt",
        user_content=f"Company signal candidates:\n{candidate_evals}",
        default_fallback=candidate_evals,
    )

    eval_map = {item.get("company_name"): item for item in structured_data if isinstance(item, dict)}

    provisional_opportunities: list[Opportunity] = []
    qualified_count = 0

    for comp, sigs in company_signals.items():
        eval_data = eval_map.get(comp) or _evaluate_heuristic(sigs[0], intent)

        hi = float(eval_data.get("hiring_intent", 80.0))
        dm = float(eval_data.get("decision_maker", 60.0))
        cf = float(eval_data.get("company_fit", 80.0))
        fr = float(eval_data.get("freshness", 85.0))
        ur = float(eval_data.get("urgency", 70.0))
        ec = float(eval_data.get("evidence_confidence", 85.0))

        score, breakdown, temp = calculate_opportunity_score(
            hiring_intent=hi,
            decision_maker=dm,
            company_fit=cf,
            freshness=fr,
            urgency=ur,
            evidence_confidence=ec,
            settings=settings,
        )

        all_roles = list({r for s in sigs for r in s.detected_roles})
        all_evidence = list({pid for s in sigs for pid in s.evidence_post_ids})

        opp_id = f"opp-{abs(hash(comp)) % 1000000:06d}"

        opp = Opportunity(
            id=opp_id,
            company_name=comp,
            score=score,
            temperature=temp,
            score_breakdown=breakdown,
            hiring_intent=hi,
            decision_maker_probability=dm,
            company_fit=cf,
            freshness=fr,
            urgency=ur,
            evidence_confidence=ec,
            detected_roles=all_roles,
            evidence_post_ids=all_evidence,
            why_detected=[s.explanation for s in sigs],
            why_now=eval_data.get("why_now", "Active hiring detected."),
            recommended_action="Inspect source posts and verify leadership stakeholder.",
            confidence=round(ec / 100.0, 2),
            contacts=[],
            status="new",
        )
        provisional_opportunities.append(opp)

        if score >= settings.qualification_threshold:
            qualified_count += 1

    # Sort opportunities descending by score
    provisional_opportunities.sort(key=lambda o: o.score, reverse=True)

    event = AgentEvent(
        node="Qualification Agent",
        status="completed",
        summary=f"Qualified {qualified_count} of {len(provisional_opportunities)} opportunities (threshold >= {settings.qualification_threshold})",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={"qualified_count": qualified_count, "total": len(provisional_opportunities)},
    )

    existing_events = list(state.get("agent_events", []))
    existing_events.append(event.model_dump())

    metrics = dict(state.get("metrics", {}))
    metrics["opportunities_count"] = len(provisional_opportunities)
    metrics["qualified_count"] = qualified_count

    logger.info(
        "qualification_completed",
        total=len(provisional_opportunities),
        qualified=qualified_count,
    )

    return {
        "opportunities": provisional_opportunities,
        "metrics": metrics,
        "agent_events": existing_events,
    }
