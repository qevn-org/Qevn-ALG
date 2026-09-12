"""Signal taxonomy and structured representation."""

from enum import Enum

from pydantic import BaseModel, Field


class SignalType(str, Enum):
    """Categorization of commercial and hiring signals."""

    HIRING = "HIRING"
    HIRING_ACCELERATION = "HIRING_ACCELERATION"
    ENGINEERING_EXPANSION = "ENGINEERING_EXPANSION"
    URGENT_HIRING = "URGENT_HIRING"
    ROLE_SPECIFIC_HIRING = "ROLE_SPECIFIC_HIRING"
    TEAM_GROWTH = "TEAM_GROWTH"
    FUNDING_RELATED_GROWTH = "FUNDING_RELATED_GROWTH"
    LOCATION_EXPANSION = "LOCATION_EXPANSION"
    LEADERSHIP_CHANGE = "LEADERSHIP_CHANGE"
    TECHNOLOGY_CHANGE = "TECHNOLOGY_CHANGE"


class Signal(BaseModel):
    """Structured evidence-backed signal extracted from posts."""

    signal_type: str = Field(description="Signal classification code")
    company_name: str = Field(default="", description="Associated company")
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence 0.0-1.0")
    urgency: float = Field(default=0.5, ge=0.0, le=1.0, description="Urgency index 0.0-1.0")
    evidence_post_ids: list[str] = Field(
        default_factory=list, description="IDs of source posts proving this signal"
    )
    detected_roles: list[str] = Field(default_factory=list, description="Specific job roles detected")
    detected_locations: list[str] = Field(default_factory=list, description="Locations mentioned in post")
    detected_decision_makers: list[str] = Field(
        default_factory=list, description="Stakeholders mentioned or authoring"
    )
    explanation: str = Field(description="Evidence-grounded explanation of the detected signal")


# Backward compatibility alias
SignalClassification = Signal
