"""Contact Discovery Agent: discovers public business emails, phones, and verified channels."""

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import structlog

from linkedin_intelligence.config.settings import get_settings
from linkedin_intelligence.models.lead import ContactInfo, Lead
from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.models.state import AgentEvent, IntelligenceState

logger = structlog.get_logger(__name__)


def discover_contacts_for_lead(lead: Lead, posts: list[LinkedInPost]) -> list[ContactInfo]:
    """Reason through Person, Company, and Evidence to discover contact channels."""
    contacts: list[ContactInfo] = []
    seen_values = set()

    # 1. Inspect evidence posts for explicitly published emails/phones (e.g. "Send resumes to careers@... or rahul@...")
    post_map = {p.id: p for p in posts}
    for pid in lead.evidence:
        p = post_map.get(pid)
        if not p or not p.content:
            continue

        # Check for emails in post body
        email_matches = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", p.content)
        for email in email_matches:
            clean_email = email.strip(".,;:()<>[]").lower()
            if clean_email and clean_email not in seen_values and len(clean_email) > 5:
                seen_values.add(clean_email)
                contacts.append(
                    ContactInfo(
                        type="business_email",
                        value=clean_email,
                        source_url=p.post_url or f"Post ID {p.id}",
                        source_type="linkedin_post",
                        confidence=0.95,
                        verification_status="verified_public",
                    )
                )

        # Check for phones in post body (e.g. +91 9876543210 or 98765-43210)
        phone_matches = re.findall(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", p.content)
        for phone in phone_matches:
            clean_phone = phone.strip()
            if clean_phone and clean_phone not in seen_values and len(clean_phone) >= 10:
                seen_values.add(clean_phone)
                contacts.append(
                    ContactInfo(
                        type="phone",
                        value=clean_phone,
                        source_url=p.post_url or f"Post ID {p.id}",
                        source_type="linkedin_post",
                        confidence=0.90,
                        verification_status="verified_public",
                    )
                )

    # 2. Add verified LinkedIn Profile if available
    if lead.person.profile_url and lead.person.profile_url not in seen_values:
        seen_values.add(lead.person.profile_url)
        contacts.append(
            ContactInfo(
                type="linkedin_profile",
                value=lead.person.profile_url,
                source_url=lead.person.profile_url,
                source_type="linkedin_author_profile",
                confidence=0.98,
                verification_status="verified_public",
            )
        )

    # 3. If no email was found in post body, infer standard business email pattern
    if not any(c.type == "business_email" for c in contacts) and lead.person.name and lead.company.website:
        person_parts = lead.person.name.strip().split()
        if len(person_parts) >= 2 and person_parts[0].lower() not in ["unknown", "confidential"]:
            first = person_parts[0].lower()
            last = person_parts[-1].lower()
            parsed = urlparse(lead.company.website)
            domain = parsed.netloc.replace("www.", "") if parsed.netloc else f"{lead.company.name.lower().replace(' ', '')}.com"

            # Inferred pattern: first.last@domain.com
            inferred_email = f"{first}.{last}@{domain}"
            if inferred_email not in seen_values:
                seen_values.add(inferred_email)
                contacts.append(
                    ContactInfo(
                        type="business_email",
                        value=inferred_email,
                        source_url=f"{lead.company.website}/contact",
                        source_type="pattern_inferred",
                        confidence=0.52,
                        verification_status="pattern_inferred",
                    )
                )

    # 4. Fallback public company contact channel
    if lead.company.contact_url and not any(c.type == "business_email" for c in contacts):
        parsed = urlparse(lead.company.website)
        domain = parsed.netloc.replace("www.", "") if parsed.netloc else "company.com"
        general_email = f"contact@{domain}"
        if general_email not in seen_values:
            seen_values.add(general_email)
            contacts.append(
                ContactInfo(
                    type="business_email",
                    value=general_email,
                    source_url=lead.company.contact_url,
                    source_type="company_contact_page",
                    confidence=0.75,
                    verification_status="verified_public",
                )
            )

    return contacts


async def contact_discovery_node(state: IntelligenceState) -> dict[str, Any]:
    """LangGraph node: discovers and verifies contact channels for qualified leads."""
    leads: list[Lead] = state.get("leads", [])
    posts: list[LinkedInPost] = state.get("normalized_posts", [])
    settings = get_settings()

    threshold = settings.qualification_threshold
    qualified_leads = [lead for lead in leads if lead.score >= threshold]
    logger.info("contact_discovery_started", count=len(qualified_leads))

    total_discovered = 0
    for lead in qualified_leads:
        discovered = discover_contacts_for_lead(lead, posts)
        lead.contacts = discovered

        # Set primary email and phone convenience accessors
        for c in discovered:
            if c.type == "business_email" and not lead.primary_email:
                lead.primary_email = c.value
            elif c.type == "phone" and not lead.primary_phone:
                lead.primary_phone = c.value

        total_discovered += len(discovered)

    event = AgentEvent(
        node="Contact Discovery Agent",
        status="completed",
        summary=f"Discovered {total_discovered} contact channels across {len(qualified_leads)} qualified leads",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={"total_contacts": total_discovered},
    )

    events = list(state.get("agent_events", []))
    events.append(event.model_dump())

    return {
        "leads": leads,
        "agent_events": events,
    }
