"""Deterministic services module."""

from linkedin_intelligence.services.deduplication import deduplicate_posts
from linkedin_intelligence.services.evidence import EvidenceService
from linkedin_intelligence.services.normalization import (
    canonicalize_url,
    compute_content_hash,
    normalize_post,
    normalize_results,
)
from linkedin_intelligence.services.scoring import (
    calculate_opportunity_score,
    classify_temperature,
)

__all__ = [
    "EvidenceService",
    "calculate_opportunity_score",
    "canonicalize_url",
    "classify_temperature",
    "compute_content_hash",
    "deduplicate_posts",
    "normalize_post",
    "normalize_results",
]
