"""Opportunity and decision maker domain models."""

from typing import Literal

from pydantic import BaseModel, Field


class StakeholderStatus(str):
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    UNKNOWN = "unknown"


class Contact(BaseModel):
    """Stakeholder or decision maker identified with supporting evidence."""

    name: str
    headline: str | None = None
    role_type: str = "Stakeholder"
    profile_url: str | None = None
    status: Literal["confirmed", "probable", "unknown"] = "probable"
    source_post_id: str | None = None
    notes: str = ""


class ScoreBreakdown(BaseModel):
    """Transparent mathematical component breakdown of the 0-100 score."""

    hiring_intent_score: float = Field(..., description="0-100 component score")
    hiring_intent_weight: float = 0.30
    decision_maker_score: float = Field(..., description="0-100 component score")
    decision_maker_weight: float = 0.20
    company_fit_score: float = Field(..., description="0-100 component score")
    company_fit_weight: float = 0.20
    freshness_score: float = Field(..., description="0-100 component score")
    freshness_weight: float = 0.15
    urgency_score: float = Field(..., description="0-100 component score")
    urgency_weight: float = 0.10
    evidence_confidence_score: float = Field(..., description="0-100 component score")
    evidence_confidence_weight: float = 0.05
    total_score: float = Field(..., description="Weighted total 0-100")


class Opportunity(BaseModel):
    """Primary actionable business opportunity entity."""

    id: str
    company_name: str
    score: float = Field(ge=0.0, le=100.0, description="Overall score 0-100")
    temperature: Literal["HOT", "WARM", "LOW"]
    score_breakdown: ScoreBreakdown

    # Quick metric accessors (0-100)
    hiring_intent: float = 0.0
    decision_maker_probability: float = 0.0
    company_fit: float = 0.0
    freshness: float = 0.0
    urgency: float = 0.0
    evidence_confidence: float = 0.0

    detected_roles: list[str] = Field(default_factory=list)
    evidence_post_ids: list[str] = Field(default_factory=list)
    why_detected: list[str] = Field(default_factory=list)
    why_now: str
    recommended_action: str
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence 0.0-1.0")
    contacts: list[Contact] = Field(default_factory=list)
    status: Literal["new", "reviewed", "in_progress", "contacted", "dismissed"] = "new"

    # Enrichment fields (explicitly marked unknown if unverified)
    industry: str = "unknown"
    company_size: str = "unknown"
    location: str = "unknown"
    website: str | None = None
