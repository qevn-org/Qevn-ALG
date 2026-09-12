"""Unit tests for deterministic scoring and temperature classification."""

from linkedin_intelligence.services.scoring import (
    calculate_opportunity_score,
    classify_temperature,
)


def test_classify_temperature():
    assert classify_temperature(95.0) == "HOT"
    assert classify_temperature(80.0) == "HOT"
    assert classify_temperature(79.9) == "WARM"
    assert classify_temperature(60.0) == "WARM"
    assert classify_temperature(59.9) == "LOW"
    assert classify_temperature(10.0) == "LOW"


def test_calculate_opportunity_score_weights():
    # Weights: Hiring Intent 30%, DM 20%, Company Fit 20%, Freshness 15%, Urgency 10%, Confidence 5%
    # If all inputs are 100, score must be 100
    score, breakdown, temp = calculate_opportunity_score(
        hiring_intent=100.0,
        decision_maker=100.0,
        company_fit=100.0,
        freshness=100.0,
        urgency=100.0,
        evidence_confidence=100.0,
    )
    assert score == 100.0
    assert temp == "HOT"
    assert breakdown.total_score == 100.0


def test_calculate_opportunity_score_weighted_math():
    score, breakdown, temp = calculate_opportunity_score(
        hiring_intent=90.0,  # 90 * 0.30 = 27
        decision_maker=80.0,  # 80 * 0.20 = 16
        company_fit=90.0,  # 90 * 0.20 = 18
        freshness=80.0,  # 80 * 0.15 = 12
        urgency=70.0,  # 70 * 0.10 = 7
        evidence_confidence=90.0,  # 90 * 0.05 = 4.5
    )
    # Sum = 27 + 16 + 18 + 12 + 7 + 4.5 = 84.5
    assert score == 84.5
    assert temp == "HOT"


def test_calculate_opportunity_score_low_band():
    score, breakdown, temp = calculate_opportunity_score(
        hiring_intent=40.0,
        decision_maker=30.0,
        company_fit=50.0,
        freshness=40.0,
        urgency=20.0,
        evidence_confidence=50.0,
    )
    assert score < 60.0
    assert temp == "LOW"
