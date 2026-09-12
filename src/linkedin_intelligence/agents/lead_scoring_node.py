"""Lead Scoring Node: Extracts 18-dim feature vector and calculates Hybrid/ML lead scores."""

import uuid
from datetime import datetime, timezone

import structlog

from linkedin_intelligence.db.repository import get_lead_repository
from linkedin_intelligence.models.lead import (
    Company,
    Lead,
    LeadIntent,
    LeadSource,
    Person,
)
from linkedin_intelligence.models.opportunities import Opportunity
from linkedin_intelligence.models.state import AgentEvent, IntelligenceState
from linkedin_intelligence.services.company_aggregation import aggregate_company_signals
from linkedin_intelligence.services.ml_scoring import (
    extract_lead_features,
    get_ml_scoring_service,
)

logger = structlog.get_logger(__name__)


async def lead_scoring_node(state: IntelligenceState) -> dict:
    """Extract features, apply multi-post boost, score via Hybrid/ML, and create canonical Leads."""
    opportunities: list[Opportunity] = state.get("opportunities", [])
    posts = state.get("normalized_posts", [])
    signals = state.get("signals", [])

    # 1. Aggregate multi-post company signals
    company_profiles = aggregate_company_signals(posts, signals)

    scoring_service = get_ml_scoring_service()
    repo = get_lead_repository()

    post_map = {p.id: p for p in posts}
    leads: list[Lead] = []

    for opp in opportunities:
        comp_key = (opp.company_name or "").strip().lower()
        profile = company_profiles.get(comp_key)

        # First post context
        first_pid = opp.evidence_post_ids[0] if opp.evidence_post_ids else None
        first_post = post_map.get(first_pid) if first_pid else None

        # Primary contact / person from opportunity contacts or post author
        if opp.contacts:
            top_contact = opp.contacts[0]
            prof_url = top_contact.profile_url
            if not prof_url and first_post and first_post.url:
                import re
                m = re.search(r"linkedin\.com/posts/([a-zA-Z0-9\-_]+)_", first_post.url)
                if m:
                    prof_url = f"https://www.linkedin.com/in/{m.group(1)}"
            person = Person(
                name=top_contact.name,
                job_title=top_contact.headline or top_contact.role_type,
                headline=top_contact.headline,
                profile_url=prof_url,
                role_type=top_contact.role_type,
                is_decision_maker=top_contact.status == "confirmed",
                decision_maker_status=top_contact.status,
            )
        elif first_post and first_post.author_name:
            import re
            prof_url = first_post.author_profile_url
            if not prof_url and first_post.url:
                m = re.search(r"linkedin\.com/posts/([a-zA-Z0-9\-_]+)_", first_post.url)
                if m:
                    prof_url = f"https://www.linkedin.com/in/{m.group(1)}"
                elif "linkedin.com/in/" in first_post.url:
                    m2 = re.search(r"(https://[a-z\.]*linkedin\.com/in/[a-zA-Z0-9\-_]+)", first_post.url)
                    if m2:
                        prof_url = m2.group(1)

            hl = first_post.author_headline or "Hiring Stakeholder"
            is_dm = any(
                t in hl.lower()
                for t in ["founder", "ceo", "cto", "vp", "director", "head of", "recruiter", "talent", "owner", "partner"]
            )
            person = Person(
                name=first_post.author_name,
                job_title=hl,
                headline=hl,
                profile_url=prof_url,
                role_type="Author / Stakeholder",
                is_decision_maker=is_dm,
                decision_maker_status="confirmed" if is_dm else "probable",
            )
        else:
            person = Person(
                name=f"{opp.company_name} Hiring Team",
                job_title="Hiring Stakeholder",
                profile_url=None,
                is_decision_maker=False,
                decision_maker_status="unknown",
            )

        # Discover contacts from author profile and post body
        from linkedin_intelligence.models.lead import ContactInfo
        lead_contacts: list[ContactInfo] = []
        seen_vals = set()

        if person.profile_url:
            lead_contacts.append(
                ContactInfo(
                    type="linkedin_profile",
                    value=person.profile_url,
                    source_url=person.profile_url,
                    source_type="linkedin_author_profile",
                    confidence=0.98,
                    verification_status="verified_public",
                )
            )
            seen_vals.add(person.profile_url)

        best_email = None
        for pid in opp.evidence_post_ids:
            p = post_map.get(pid)
            if p and p.content:
                import re
                email_matches = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", p.content)
                for email in email_matches:
                    clean_email = email.strip(".,;:()<>[]").lower()
                    if clean_email and clean_email not in seen_vals and len(clean_email) > 5:
                        seen_vals.add(clean_email)
                        if not best_email:
                            best_email = clean_email
                        lead_contacts.append(
                            ContactInfo(
                                type="business_email",
                                value=clean_email,
                                source_url=p.url or f"Post ID {p.id}",
                                source_type="linkedin_post",
                                confidence=0.95,
                                verification_status="verified_public",
                            )
                        )

        source = LeadSource(
            post_id=first_pid,
            post_url=first_post.post_url if first_post else None,
            post_date=first_post.published_at if first_post else None,
            author_name=first_post.author_name if first_post else person.name,
            author_headline=first_post.author_headline if first_post else person.job_title,
            raw_post_content=first_post.content if first_post else None,
        )

        detected_roles = ", ".join(opp.detected_roles[:3]) if opp.detected_roles else "Software Development"
        intent = LeadIntent(
            detected_intent="Hiring" if opp.hiring_intent >= 60 else "Vendor / Project",
            signal_type="HIRING_SIGNAL" if opp.hiring_intent >= 60 else "PROJECT_EXPANSION",
            detected_requirement=detected_roles,
            technology_need=detected_roles,
            urgency=opp.urgency,
        )

        comp = Company(
            name=opp.company_name,
            industry=opp.industry if opp.industry != "unknown" else "Technology & Software",
            location=opp.location if opp.location != "unknown" else "India",
            company_size=opp.company_size if opp.company_size != "unknown" else "Mid-Market",
            website=opp.website,
        )

        lead_id = f"lead-{uuid.uuid5(uuid.NAMESPACE_DNS, f'{opp.company_name}-{person.name}').hex[:10]}"

        lead = Lead(
            id=lead_id,
            status="new",
            company=comp,
            person=person,
            source=source,
            intent=intent,
            contacts=lead_contacts,
            primary_email=best_email,
            evidence=list(opp.evidence_post_ids),
            signals=list(opp.why_detected),
            why_detected=list(opp.why_detected),
            why_now=opp.why_now,
            recommended_action=opp.recommended_action,
        )


        # 2. Extract 18-dim feature vector
        features = extract_lead_features(lead, profile)

        # 3. Score via Hybrid/ML engine
        score, temp, scoring_mode = scoring_service.predict_lead(features)
        lead.score = score
        lead.temperature = temp
        lead.feature_vector = features

        leads.append(lead)

    # Persist leads into SQLite repository
    repo.upsert_leads(leads)

    hot_count = sum(1 for lead in leads if lead.temperature == "HOT")
    warm_count = sum(1 for lead in leads if lead.temperature == "WARM")
    cool_count = sum(1 for lead in leads if lead.temperature == "COOL")
    cold_count = sum(1 for lead in leads if lead.temperature == "COLD")
    unqualified = sum(1 for lead in leads if lead.temperature == "UNQUALIFIED")

    event = AgentEvent(
        node="Lead Scoring & Feature Extraction",
        status="completed",
        summary=f"Scored {len(leads)} leads via {scoring_service.get_metrics().status_message} (HOT: {hot_count}, WARM: {warm_count}, COOL: {cool_count})",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={
            "total_leads": len(leads),
            "hot": hot_count,
            "warm": warm_count,
            "cool": cool_count,
            "cold": cold_count,
            "unqualified": unqualified,
        },
    )

    events = list(state.get("agent_events", []))
    events.append(event.model_dump())

    return {
        "leads": leads,
        "agent_events": events,
    }
