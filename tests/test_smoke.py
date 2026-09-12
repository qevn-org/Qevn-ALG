"""Smoke tests verifying the complete end-to-end intelligence pipeline."""

import pytest

from linkedin_intelligence.config.settings import get_settings
from linkedin_intelligence.models.search import SearchPlan
from linkedin_intelligence.services.deduplication import deduplicate_posts
from linkedin_intelligence.services.normalization import normalize_results
from linkedin_intelligence.services.scoring import calculate_opportunity_score
from linkedin_intelligence.tools.retrieval_service import LinkedInRetrievalService


@pytest.mark.asyncio
async def test_pipeline_smoke():
    # 1. Environment & Settings
    settings = get_settings()
    assert settings.app_env in ["development", "staging", "production"]

    # 2. Retrieval Service
    retrieval = LinkedInRetrievalService(settings)
    plan = SearchPlan(queries=["hiring backend engineer Bangalore", "hiring software engineer India"])
    raw_posts = await retrieval.search(plan)
    assert len(raw_posts) > 0

    # 3. Normalization
    posts = normalize_results(raw_posts, matched_query="smoke_test")
    assert len(posts) > 0
    assert posts[0].content

    # 4. Deduplication
    unique_posts, dedup_stats = deduplicate_posts(posts)
    assert len(unique_posts) > 0
    assert "duplicates_removed" in dedup_stats

    # 5. Scoring
    score, breakdown, temp = calculate_opportunity_score(
        hiring_intent=85.0,
        decision_maker=80.0,
        company_fit=90.0,
        freshness=85.0,
        urgency=75.0,
        evidence_confidence=90.0,
        settings=settings,
    )
    assert 0.0 <= score <= 100.0
    assert temp in ["HOT", "WARM", "LOW"]
    assert breakdown.total_score == score


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_apify_opt_in():
    """Opt-in test run with `pytest -m live` when APIFY_TOKEN is configured."""
    settings = get_settings()
    if not settings.has_apify:
        pytest.skip("APIFY_TOKEN not configured; skipping live test.")

    retrieval = LinkedInRetrievalService(settings)
    plan = SearchPlan(queries=["hiring backend engineer"], max_queries=1)
    results = await retrieval.search(plan)
    assert isinstance(results, list)
