"""Deterministic Normalization and Deduplication workflow nodes."""

from datetime import datetime, timezone

import structlog

from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.models.state import AgentEvent, IntelligenceState
from linkedin_intelligence.services.deduplication import deduplicate_posts
from linkedin_intelligence.services.normalization import normalize_results

logger = structlog.get_logger(__name__)


def normalization_node(state: IntelligenceState) -> dict:
    """Deterministically normalize heterogeneous raw scraper items to typed LinkedInPost models."""
    raw_results = state.get("raw_results", [])
    normalized = normalize_results(raw_results)

    event = AgentEvent(
        node="Normalization",
        status="completed",
        summary=f"Normalized {len(normalized)} posts with canonical URLs and parsed metadata",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={"raw_count": len(raw_results), "normalized_count": len(normalized)},
    )

    existing_events = list(state.get("agent_events", []))
    existing_events.append(event.model_dump())

    metrics = dict(state.get("metrics", {}))
    metrics["normalized_count"] = len(normalized)

    logger.info("normalization_node_completed", count=len(normalized))
    return {
        "normalized_posts": normalized,
        "metrics": metrics,
        "agent_events": existing_events,
    }


def deduplication_node(state: IntelligenceState) -> dict:
    """Deterministically deduplicate posts across URL, ID, and content hash."""
    posts: list[LinkedInPost] = state.get("normalized_posts", [])
    unique_posts, stats = deduplicate_posts(posts)

    event = AgentEvent(
        node="Deduplication",
        status="completed",
        summary=f"Deduplicated to {len(unique_posts)} unique posts (removed {stats['duplicates_removed']} duplicates)",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data=stats,
    )

    existing_events = list(state.get("agent_events", []))
    existing_events.append(event.model_dump())

    metrics = dict(state.get("metrics", {}))
    metrics["unique_posts_count"] = len(unique_posts)
    metrics["duplicates_removed"] = stats["duplicates_removed"]

    logger.info("deduplication_node_completed", **stats)
    return {
        "normalized_posts": unique_posts,
        "metrics": metrics,
        "agent_events": existing_events,
    }
