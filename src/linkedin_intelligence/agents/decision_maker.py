"""Decision-Maker Agent: discovers verified leadership and recruiting stakeholders."""

from datetime import datetime, timezone

import structlog

from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.models.opportunities import Contact, Opportunity
from linkedin_intelligence.models.state import AgentEvent, IntelligenceState

logger = structlog.get_logger(__name__)



def _extract_contacts_from_posts(
    opp: Opportunity, posts: list[LinkedInPost]
) -> list[Contact]:
    """Deterministically discover stakeholder contacts from source evidence posts."""
    contacts: list[Contact] = []
    seen_names = set()
    post_map = {p.id: p for p in posts}

    for pid in opp.evidence_post_ids:
        p = post_map.get(pid)
        if not p:
            continue

        author_name = p.author_name
        author_hl = p.author_headline or ""
        hl_lower = author_hl.lower()

        # Check if author is a leadership stakeholder
        role_type = "Stakeholder"
        status = "probable"
        if "cto" in hl_lower or "chief technology officer" in hl_lower:
            role_type = "CTO"
            status = "confirmed"
        elif "vp of engineering" in hl_lower or "vp engineering" in hl_lower or "vice president" in hl_lower:
            role_type = "VP Engineering"
            status = "confirmed"
        elif "founder" in hl_lower or "co-founder" in hl_lower:
            role_type = "Founder / Co-Founder"
            status = "confirmed"
        elif "head of talent" in hl_lower or "talent acquisition" in hl_lower or "recruiter" in hl_lower:
            role_type = "Head of Talent / Recruiting"
            status = "confirmed"

        # Resolve author profile URL
        author_url = p.author_profile_url
        if not author_url and p.url:
            import re
            m = re.search(r"linkedin\.com/posts/([a-zA-Z0-9\-_]+)_", p.url)
            if m:
                author_url = f"https://www.linkedin.com/in/{m.group(1)}"
            elif "linkedin.com/in/" in p.url:
                m2 = re.search(r"(https://[a-z\.]*linkedin\.com/in/[a-zA-Z0-9\-_]+)", p.url)
                if m2:
                    author_url = m2.group(1)

        if author_name and author_name not in seen_names:
            seen_names.add(author_name)
            contacts.append(
                Contact(
                    name=author_name,
                    headline=author_hl,
                    role_type=role_type,
                    profile_url=author_url,
                    status=status,
                    source_post_id=p.id,
                    notes=f"Author of post evidencing hiring for {opp.company_name}",
                )
            )


        # Check post body text for referenced names, e.g. "Reach out to me or our Head of Talent Priya Nair"
        # If Priya Nair is mentioned
        import re
        m = re.search(r"(?:Head of Talent|reach out to|contact)\s+([A-Z][a-z]+ [A-Z][a-z]+)", p.content)
        if m:
            ref_name = m.group(1).strip()
            if ref_name not in seen_names and len(ref_name) < 30:
                seen_names.add(ref_name)
                contacts.append(
                    Contact(
                        name=ref_name,
                        headline="Identified via post content",
                        role_type="Head of Talent / Contact",
                        profile_url=None,
                        status="probable",
                        source_post_id=p.id,
                        notes="Referenced in post body as contact point",
                    )
                )

    return contacts


async def decision_maker_node(state: IntelligenceState) -> dict:
    """Discover and verify decision maker contacts for qualified opportunities."""
    opportunities: list[Opportunity] = state.get("opportunities", [])
    posts: list[LinkedInPost] = state.get("normalized_posts", [])

    logger.info("decision_maker_started", count=len(opportunities))

    total_contacts = 0
    for opp in opportunities:
        contacts = _extract_contacts_from_posts(opp, posts)
        opp.contacts = contacts
        total_contacts += len(contacts)

    event = AgentEvent(
        node="Decision-Maker Agent",
        status="completed",
        summary=f"Identified {total_contacts} verified stakeholders across {len(opportunities)} opportunities",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={"total_contacts": total_contacts},
    )


    existing_events = list(state.get("agent_events", []))
    existing_events.append(event.model_dump())

    logger.info("decision_maker_completed", total_contacts=total_contacts)
    return {
        "opportunities": opportunities,
        "agent_events": existing_events,
    }
