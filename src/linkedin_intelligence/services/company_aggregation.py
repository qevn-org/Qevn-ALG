"""Multi-post signal aggregation engine building company intelligence profiles."""

from collections import defaultdict

import structlog

from linkedin_intelligence.models.lead import CompanySignalProfile
from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.models.signals import Signal

logger = structlog.get_logger(__name__)


def aggregate_company_signals(
    posts: list[LinkedInPost],
    signals: list[Signal],
) -> dict[str, CompanySignalProfile]:
    """Aggregate multi-post evidence per company into unified signal profiles."""
    posts_by_company: dict[str, list[LinkedInPost]] = defaultdict(list)
    for p in posts:
        name = (p.company_name or "").strip()
        if not name or name.lower() in ["unknown", "confidential", "stealth"]:
            continue
        posts_by_company[name.lower()].append(p)

    signals_by_company: dict[str, list[Signal]] = defaultdict(list)
    for s in signals:
        name = (s.company_name or "").strip().lower()
        if name:
            signals_by_company[name].append(s)

    profiles: dict[str, CompanySignalProfile] = {}

    for comp_key, comp_posts in posts_by_company.items():
        comp_name = comp_posts[0].company_name or comp_key.title()
        comp_signals = signals_by_company.get(comp_key, [])

        all_text = " ".join(p.content.lower() for p in comp_posts)

        # Detect distinct signal categories
        detected_signals = set()
        for s in comp_signals:
            detected_signals.add(s.signal_type.replace("_", " ").title())

        # Check for multi-post hiring, digital transformation, vendor search
        if any(w in all_text for w in ["hiring", "looking for", "join our team", "opening"]):
            detected_signals.add("Active Hiring")

        digital_trans = any(w in all_text for w in ["digital transformation", "cloud migration", "ai transformation", "modernize", "overhaul"])
        if digital_trans:
            detected_signals.add("Digital Transformation")

        vendor_search = any(w in all_text for w in ["agency", "partner", "rfp", "vendor", "outsource", "consultant"])
        if vendor_search:
            detected_signals.add("Vendor / Partner Search")

        tech_investment = any(w in all_text for w in ["investing in", "stack upgrade", "building platform", "series a", "series b", "seed"])
        if tech_investment:
            detected_signals.add("Technology Investment")

        post_count = len(comp_posts)
        signal_count = len(detected_signals) + len(comp_signals)

        # Compute hiring velocity
        if post_count >= 4:
            hiring_velocity = "Aggressive"
        elif post_count >= 2:
            hiring_velocity = "High"
        else:
            hiring_velocity = "Moderate"

        # Compute technology intent
        if vendor_search and digital_trans:
            tech_intent = "Very High"
        elif vendor_search or digital_trans or "Technology Investment" in detected_signals:
            tech_intent = "High"
        else:
            tech_intent = "Moderate"

        # Calculate boost: 0 to 20 points based on multi-post density
        boost = 0.0
        if post_count > 1:
            boost += min(12.0, (post_count - 1) * 4.0)
        if vendor_search:
            boost += 5.0
        if digital_trans:
            boost += 3.0

        post_ids = [p.id for p in comp_posts]

        profile = CompanySignalProfile(
            company_name=comp_name,
            signals=sorted(list(detected_signals)),
            signal_count=signal_count,
            post_count=post_count,
            hiring_velocity=hiring_velocity,
            technology_intent=tech_intent,
            digital_transformation=digital_trans,
            vendor_search=vendor_search,
            evidence_post_ids=post_ids,
            aggregated_score_boost=round(boost, 1),
        )
        profiles[comp_key] = profile

    logger.info("aggregated_company_signals", company_count=len(profiles))
    return profiles
