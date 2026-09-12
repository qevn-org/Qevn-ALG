"""Unit tests for Pydantic domain models."""

import pytest
from pydantic import ValidationError

from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.models.opportunities import (
    Contact,
    Opportunity,
    ScoreBreakdown,
)
from linkedin_intelligence.models.search import (
    ActorSearchInput,
    SearchIntent,
    SearchPlan,
)


def test_search_intent_defaults():
    intent = SearchIntent(objective="Find engineering hiring")
    assert intent.signal_type == "hiring"
    assert intent.freshness_days == 7
    assert isinstance(intent.target_roles, list)


def test_actor_search_input_validation():
    # Valid input
    valid = ActorSearchInput(searchQueries=["hiring backend engineer"])
    assert len(valid.searchQueries) == 1

    # Empty queries should fail validation
    with pytest.raises(ValidationError):
        ActorSearchInput(searchQueries=[])


def test_search_plan_validation():
    plan = SearchPlan(queries=["q1", "q2"], max_queries=15, rationale="Test")
    assert len(plan.queries) == 2
    assert plan.max_queries == 15


def test_linkedin_post_model():
    post = LinkedInPost(
        id="post-123",
        content="We are hiring senior engineers!",
        author_name="Alice Smith",
        company_name="Acme",
    )
    assert post.clean_text == "We are hiring senior engineers!"
    assert post.content_preview == "We are hiring senior engineers!"


def test_opportunity_model():
    breakdown = ScoreBreakdown(
        hiring_intent_score=90.0,
        decision_maker_score=80.0,
        company_fit_score=85.0,
        freshness_score=90.0,
        urgency_score=75.0,
        evidence_confidence_score=95.0,
        total_score=86.5,
    )
    opp = Opportunity(
        id="opp-1",
        company_name="Acme Corp",
        score=86.5,
        temperature="HOT",
        score_breakdown=breakdown,
        why_detected=["Active hiring post detected"],
        why_now="Recent hiring momentum",
        recommended_action="Contact CTO",
        confidence=0.95,
        contacts=[Contact(name="Bob Jones", role_type="CTO", status="confirmed")],
    )
    assert opp.score == 86.5
    assert opp.temperature == "HOT"
    assert len(opp.contacts) == 1
    assert opp.contacts[0].status == "confirmed"
