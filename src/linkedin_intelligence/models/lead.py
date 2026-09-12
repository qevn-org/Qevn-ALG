"""Canonical Lead, Contact, Company, and Outcome domain models."""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

LeadTemperature = Literal["HOT", "WARM", "COOL", "COLD", "UNQUALIFIED", "OTHER"]

LeadStatus = Literal[
    "new",
    "reviewed",
    "in_progress",
    "contacted",
    "responded",
    "meeting",
    "won",
    "lost",
    "disqualified",
]

ContactVerificationStatus = Literal["verified_public", "pattern_inferred", "unverified"]


class ContactInfo(BaseModel):
    """Specific contact channel discovered for a lead."""

    type: Literal["business_email", "phone", "linkedin_profile", "alternate"] = "business_email"
    value: str
    source_url: str | None = None
    source_type: str = "web_search"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    verification_status: ContactVerificationStatus = "pattern_inferred"


class Person(BaseModel):
    """Person or stakeholder associated with the lead."""

    name: str = "Unknown"
    job_title: str = "Unknown"
    headline: str | None = None
    profile_url: str | None = None
    role_type: str = "Stakeholder"
    is_decision_maker: bool = False
    decision_maker_status: Literal["confirmed", "probable", "unknown"] = "unknown"
    confidence: float = 0.5

    @property
    def linkedin_url(self) -> str | None:
        """Alias for profile_url."""
        return self.profile_url


class Company(BaseModel):
    """Enriched company entity."""

    name: str
    website: str | None = None
    linkedin_url: str | None = None
    industry: str = "Unknown"
    location: str = "Unknown"
    company_size: str = "Unknown"
    description: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    founded_year: int | None = None
    careers_url: str | None = None
    contact_url: str | None = None


class LeadSource(BaseModel):
    """Source provenance tracking."""

    post_id: str | None = None
    post_url: str | None = None
    post_date: str | None = None
    matched_queries: list[str] = Field(default_factory=list)
    author_name: str | None = None
    author_headline: str | None = None
    raw_post_content: str | None = None


class LeadIntent(BaseModel):
    """Detected intent classification and requirements."""

    detected_intent: str = "Hiring"
    signal_type: str = "HIRING_EXPANSION"
    detected_requirement: str = "Software Engineering"
    technology_need: str = "Backend Development"
    urgency: float = 50.0


class LeadEnrichment(BaseModel):
    """LLM and web-derived deep enrichment intelligence."""

    lead_summary: str = ""
    intent_explanation: str = ""
    business_need: str = ""
    technology_requirement: str = ""
    buying_intent: str = "Medium"
    decision_maker_probability: float = 50.0
    recommended_service: str = "Custom Software Engineering"
    recommended_outreach_angle: str = "Value-first executive reachout"
    recommended_action: str = ""
    why_this_lead: str = ""
    why_now: str = ""
    confidence: float = 0.7
    searched_at: str | None = None
    sources_checked: list[str] = Field(default_factory=list)


class CompanySignalProfile(BaseModel):
    """Multi-post aggregated company intelligence profile."""

    company_name: str
    signals: list[str] = Field(default_factory=list)
    signal_count: int = 0
    post_count: int = 1
    hiring_velocity: str = "Moderate"
    technology_intent: str = "Moderate"
    digital_transformation: bool = False
    vendor_search: bool = False
    evidence_post_ids: list[str] = Field(default_factory=list)
    aggregated_score_boost: float = 0.0


class Lead(BaseModel):
    """Canonical Master Lead Model."""

    id: str
    status: LeadStatus = "new"
    temperature: LeadTemperature = "COOL"
    score: float = Field(default=50.0, ge=0.0, le=100.0)

    person: Person = Field(default_factory=Person)
    company: Company
    source: LeadSource = Field(default_factory=LeadSource)
    intent: LeadIntent = Field(default_factory=LeadIntent)
    enrichment: LeadEnrichment = Field(default_factory=LeadEnrichment)

    contacts: list[ContactInfo] = Field(default_factory=list)
    primary_email: str | None = None
    primary_phone: str | None = None

    signals: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    why_detected: list[str] = Field(default_factory=list)
    why_now: str = ""
    recommended_action: str = ""

    outcome: str | None = None
    tags: list[str] = Field(default_factory=list)
    in_watchlist: bool = False

    first_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_enriched: str | None = None

    feature_vector: dict[str, float | int | str] = Field(default_factory=dict)

    @property
    def ml_score(self) -> float:
        """ML conversion probability or normalized score."""
        val = self.feature_vector.get("ml_probability")
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
        return round(self.score / 100.0, 3)

    @property
    def is_decision_maker(self) -> bool:
        """Convenience property referencing person.is_decision_maker."""
        return self.person.is_decision_maker

    def to_flat_dict(self) -> dict[str, Any]:
        """Flatten lead into a tabular dictionary for data tables and exports."""
        best_email = self.primary_email
        best_phone = self.primary_phone
        contact_source = None
        contact_confidence = 0.0
        contact_status = "unverified"

        for c in self.contacts:
            if c.type == "business_email" and not best_email:
                best_email = c.value
                contact_source = c.source_url or c.source_type
                contact_confidence = c.confidence
                contact_status = c.verification_status
            elif c.type == "phone" and not best_phone:
                best_phone = c.value

        # Ensure LinkColumns get None or a valid http URL (not arbitrary strings like 'Not found')
        profile_url_val = self.person.profile_url if (self.person.profile_url and self.person.profile_url.startswith("http")) else None
        post_url_val = self.source.post_url if (self.source.post_url and self.source.post_url.startswith("http")) else None
        website_val = self.company.website if (self.company.website and self.company.website.startswith("http")) else None
        company_li_val = self.company.linkedin_url if (self.company.linkedin_url and self.company.linkedin_url.startswith("http")) else None

        return {
            "id": self.id,
            "Lead Status": self.status,
            "Lead Temperature": self.temperature,
            "Lead Score": round(self.score, 1),
            "Person Name": self.person.name,
            "Job Title": self.person.job_title,
            "Company": self.company.name,
            "Industry": self.company.industry,
            "Location": self.company.location,
            "LinkedIn Profile": profile_url_val,
            "LinkedIn Post": post_url_val,
            "Post Date": self.source.post_date or "Recent",
            "Detected Intent": self.intent.detected_intent,
            "Signal Type": self.intent.signal_type,
            "Detected Requirement": self.intent.detected_requirement,
            "Technology Need": self.intent.technology_need,
            "Decision Maker Status": self.person.decision_maker_status.title(),
            "Company Website": website_val,
            "Company LinkedIn": company_li_val,
            "Business Email": best_email or "Not found",
            "Phone": best_phone or "Not found",
            "Alternate Contact": "Not found",
            "Contact Source": contact_source or "Not found",
            "Contact Confidence": f"{int(contact_confidence * 100)}%" if contact_confidence else "Not found",
            "Contact Status": contact_status,
            "Website": website_val,
            "Company Size": self.company.company_size,

            "Company Description": self.company.description or "Not found",
            "Why This Lead": self.enrichment.why_this_lead or (", ".join(self.why_detected) if self.why_detected else "Signal detected"),
            "Why Now": self.enrichment.why_now or self.why_now or "Active recruitment signal",
            "Recommended Action": self.recommended_action or self.enrichment.recommended_action or "Review lead",
            "Evidence": f"{len(self.evidence)} post citation(s)",
            "Last Enriched": self.last_enriched or "Not enriched",
            "Last Seen": self.last_seen[:10] if self.last_seen else "Today",
        }


class SearchRunRecord(BaseModel):
    """Record of an automated or user-triggered intelligence search run."""

    run_id: str
    user_query: str
    search_plan: dict[str, Any] = Field(default_factory=dict)
    queries: list[str] = Field(default_factory=list)
    start_time: str
    end_time: str | None = None
    result_count: int = 0
    normalized_count: int = 0
    duplicate_count: int = 0
    signal_count: int = 0
    qualified_count: int = 0
    enriched_count: int = 0
    error_count: int = 0


class LeadOutcomeRecord(BaseModel):
    """Historical feedback label for ML model training."""

    lead_id: str
    action: str
    label: int
    features: dict[str, float | int] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""
