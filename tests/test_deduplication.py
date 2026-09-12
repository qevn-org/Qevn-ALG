"""Unit tests for deterministic deduplication service."""

from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.services.deduplication import deduplicate_posts


def test_deduplicate_by_url():
    p1 = LinkedInPost(
        id="p1",
        url="https://www.linkedin.com/posts/acme-1",
        content="Hiring software engineers today!",
        matched_queries=["query 1"],
    )
    p2 = LinkedInPost(
        id="p2",
        url="https://www.linkedin.com/posts/acme-1",
        content="Hiring software engineers today!",
        matched_queries=["query 2"],
    )
    unique, stats = deduplicate_posts([p1, p2])
    assert len(unique) == 1
    assert stats["duplicates_removed"] == 1
    # Merges queries
    assert "query 1" in unique[0].matched_queries
    assert "query 2" in unique[0].matched_queries


def test_deduplicate_by_content_hash():
    p1 = LinkedInPost(
        id="p1",
        url=None,
        content="Urgent hiring for Python developers in Bangalore!",
        matched_queries=["q1"],
    )
    p2 = LinkedInPost(
        id="p2",
        url=None,
        content="urgent  hiring   for PYTHON developers in Bangalore!  ",
        matched_queries=["q2"],
    )
    unique, stats = deduplicate_posts([p1, p2])
    assert len(unique) == 1
    assert stats["duplicates_removed"] == 1


def test_deduplicate_by_fallback_key():
    p1 = LinkedInPost(
        id="p1",
        author_name="Rohan Sharma",
        published_at="2026-09-10T12:00:00Z",
        content="We are growing the team rapidly and looking for architects.",
        matched_queries=["q1"],
    )
    p2 = LinkedInPost(
        id="p2",
        author_name="Rohan Sharma",
        published_at="2026-09-10T12:00:00Z",
        content="We are growing the team rapidly and looking for architects.",
        matched_queries=["q2"],
    )
    unique, stats = deduplicate_posts([p1, p2])
    assert len(unique) == 1
    assert stats["duplicates_removed"] == 1
