"""Deterministic scoring and temperature classification engine."""

from typing import Literal

from linkedin_intelligence.config.settings import Settings, get_settings
from linkedin_intelligence.models.opportunities import ScoreBreakdown


def classify_temperature(
    score: float,
    hot_threshold: float = 80.0,
    warm_threshold: float = 60.0,
) -> Literal["HOT", "WARM", "LOW"]:
    """Classify 0-100 score into HOT, WARM, or LOW temperature band."""
    if score >= hot_threshold:
        return "HOT"
    elif score >= warm_threshold:
        return "WARM"
    return "LOW"


def calculate_opportunity_score(
    hiring_intent: float,
    decision_maker: float,
    company_fit: float,
    freshness: float,
    urgency: float,
    evidence_confidence: float,
    settings: Settings | None = None,
) -> tuple[float, ScoreBreakdown, Literal["HOT", "WARM", "LOW"]]:
    """Calculate deterministic weighted opportunity score and produce visible breakdown.

    All input parameters are 0-100. Returns:
        (total_score, ScoreBreakdown, temperature)
    """
    if settings is None:
        settings = get_settings()

    # Clamp values 0-100
    hi = max(0.0, min(100.0, float(hiring_intent)))
    dm = max(0.0, min(100.0, float(decision_maker)))
    cf = max(0.0, min(100.0, float(company_fit)))
    fr = max(0.0, min(100.0, float(freshness)))
    ur = max(0.0, min(100.0, float(urgency)))
    ec = max(0.0, min(100.0, float(evidence_confidence)))

    w_hi = settings.weight_hiring_intent
    w_dm = settings.weight_decision_maker
    w_cf = settings.weight_company_fit
    w_fr = settings.weight_freshness
    w_ur = settings.weight_urgency
    w_ec = settings.weight_evidence_confidence

    total_weight = w_hi + w_dm + w_cf + w_fr + w_ur + w_ec
    if total_weight <= 0:
        total_weight = 1.0

    weighted_sum = (
        (hi * w_hi)
        + (dm * w_dm)
        + (cf * w_cf)
        + (fr * w_fr)
        + (ur * w_ur)
        + (ec * w_ec)
    )
    total_score = round(weighted_sum / total_weight, 1)

    breakdown = ScoreBreakdown(
        hiring_intent_score=round(hi, 1),
        hiring_intent_weight=round(w_hi, 2),
        decision_maker_score=round(dm, 1),
        decision_maker_weight=round(w_dm, 2),
        company_fit_score=round(cf, 1),
        company_fit_weight=round(w_cf, 2),
        freshness_score=round(fr, 1),
        freshness_weight=round(w_fr, 2),
        urgency_score=round(ur, 1),
        urgency_weight=round(w_ur, 2),
        evidence_confidence_score=round(ec, 1),
        evidence_confidence_weight=round(w_ec, 2),
        total_score=total_score,
    )

    temp = classify_temperature(
        total_score,
        hot_threshold=settings.hot_threshold,
        warm_threshold=settings.qualification_threshold,
    )

    return total_score, breakdown, temp
