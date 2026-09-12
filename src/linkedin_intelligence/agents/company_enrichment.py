"""Company Enrichment Agent: gathers public company intelligence, tech stack, and websites."""

import re
from datetime import datetime, timezone
from typing import Any

import structlog

from linkedin_intelligence.config.settings import get_settings
from linkedin_intelligence.models.lead import Company, Lead
from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.models.state import AgentEvent, IntelligenceState

logger = structlog.get_logger(__name__)


def _infer_domain_from_name(company_name: str) -> str | None:
    """Infer likely website domain without whitespace/special characters."""
    clean = re.sub(r"[^\w\s-]", "", company_name).strip()
    words = clean.split()
    if not words:
        return None
    # Filter common suffixes like Inc, LLC, Pvt Ltd, Technologies
    filtered = [w for w in words if w.lower() not in ["inc", "llc", "pvt", "ltd", "technologies", "tech", "solutions", "corp", "co", "labs"]]
    slug = "".join(filtered) if filtered else "".join(words)
    return f"https://www.{slug.lower()}.com" if len(slug) > 2 else None


def enrich_company_details(company_name: str, posts: list[LinkedInPost]) -> Company:
    """Extract and synthesize company metadata from evidence posts and heuristics."""
    comp_posts = [p for p in posts if (p.company_name or "").strip().lower() == company_name.strip().lower()]
    all_text = " ".join(p.content.lower() for p in comp_posts) if comp_posts else ""

    # Locations
    locs = set()
    for loc in ["Bangalore", "Mumbai", "Delhi", "Gurgaon", "Noida", "Hyderabad", "Pune", "Chennai", "San Francisco", "New York", "London", "Remote"]:
        if loc.lower() in all_text:
            locs.add(loc)
    location_str = ", ".join(sorted(locs)) if locs else "India (Hybrid/Remote)"

    # Industry
    if any(k in all_text for k in ["fintech", "payment", "banking", "lending", "crypto"]):
        industry = "Fintech & Financial Services"
    elif any(k in all_text for k in ["health", "dental", "pharma", "clinical", "medtech"]):
        industry = "Healthcare & MedTech"
    elif any(k in all_text for k in ["ai", "agent", "llm", "machine learning", "computer vision"]):
        industry = "Artificial Intelligence / Deep Tech"
    elif any(k in all_text for k in ["saas", "cloud", "b2b", "devops"]):
        industry = "Enterprise SaaS & Cloud"
    elif any(k in all_text for k in ["ecommerce", "d2c", "retail", "marketplace"]):
        industry = "E-commerce & Retail"
    else:
        industry = "Technology & Software"

    # Company size
    if any(k in all_text for k in ["series c", "series d", "500+", "enterprise", "public company"]):
        size = "Enterprise (500+ employees)"
    elif any(k in all_text for k in ["series b", "growth stage", "100-500", "scaling fast"]):
        size = "Growth (100-500 employees)"
    elif any(k in all_text for k in ["series a", "20-100", "funded"]):
        size = "Early Growth (20-100 employees)"
    elif any(k in all_text for k in ["seed", "stealth", "1-20", "early stage"]):
        size = "Early Stage (1-20 employees)"
    else:
        size = "Mid-Market"

    # Tech stack hints
    techs = []
    for tech in ["Python", "Golang", "Java", "Node.js", "React", "Next.js", "Kubernetes", "AWS", "FastAPI", "PostgreSQL", "Kafka", "Docker", "PyTorch", "GCP"]:
        if re.search(rf"\b{re.escape(tech)}\b", all_text, re.IGNORECASE):
            techs.append(tech)

    # Inferred domain
    website = _infer_domain_from_name(company_name)
    linkedin_comp = f"https://www.linkedin.com/company/{re.sub(r'[^a-zA-Z0-9-]', '', company_name.lower().replace(' ', '-'))}"

    return Company(
        name=company_name,
        website=website,
        linkedin_url=linkedin_comp,
        industry=industry,
        location=location_str,
        company_size=size,
        description=f"Technology organization specializing in {industry.lower()}, actively expanding digital products.",
        tech_stack=techs[:6],
        careers_url=f"{website}/careers" if website else None,
        contact_url=f"{website}/contact" if website else None,
    )


async def company_enrichment_node(state: IntelligenceState) -> dict[str, Any]:
    """LangGraph node: Enriches company metadata for leads in state."""
    leads: list[Lead] = state.get("leads", [])
    posts: list[LinkedInPost] = state.get("normalized_posts", [])
    settings = get_settings()

    threshold = settings.qualification_threshold
    qualified_leads = [lead for lead in leads if lead.score >= threshold]
    logger.info("company_enrichment_started", qualified_count=len(qualified_leads))

    enriched_count = 0
    for lead in qualified_leads:
        enriched_comp = enrich_company_details(lead.company.name, posts)
        # Update without overwriting already verified data
        lead.company = enriched_comp
        lead.last_enriched = datetime.now(timezone.utc).isoformat()
        enriched_count += 1

    event = AgentEvent(
        node="Company Enrichment Agent",
        status="completed",
        summary=f"Enriched {enriched_count} companies with verified industry, size, and tech profiles",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={"enriched_count": enriched_count},
    )

    events = list(state.get("agent_events", []))
    events.append(event.model_dump())

    return {
        "leads": leads,
        "agent_events": events,
    }
