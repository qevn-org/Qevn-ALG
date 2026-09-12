"""Deterministic multi-key deduplication service."""

import hashlib

import structlog

from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.services.normalization import compute_content_hash

logger = structlog.get_logger(__name__)


def compute_fallback_key(post: LinkedInPost) -> str:
    """Fallback deduplication key using author, date, and leading content snippet."""
    author = (post.author_name or "").strip().lower()
    date_part = (post.published_at or "")[:10]
    lead = " ".join((post.content or "").lower().split())[:60]
    raw_str = f"{author}|{date_part}|{lead}"
    return hashlib.md5(raw_str.encode("utf-8")).hexdigest()[:16]


def deduplicate_posts(
    posts: list[LinkedInPost],
) -> tuple[list[LinkedInPost], dict[str, int]]:
    """Deduplicate posts using priority keys while tracking query origins.

    Returns:
        tuple of (unique_posts, stats_dict)
    """
    seen_urls: dict[str, LinkedInPost] = {}
    seen_ids: dict[str, LinkedInPost] = {}
    seen_hashes: dict[str, LinkedInPost] = {}
    seen_fallbacks: dict[str, LinkedInPost] = {}

    unique_posts: list[LinkedInPost] = []
    duplicate_count = 0

    for post in posts:
        matched_existing: LinkedInPost | None = None

        # 1. Canonical URL check
        if post.url and post.url in seen_urls:
            matched_existing = seen_urls[post.url]

        # 2. Unique ID check
        elif post.id and post.id in seen_ids:
            matched_existing = seen_ids[post.id]

        # 3. Content hash check
        else:
            c_hash = compute_content_hash(post.content)
            if c_hash in seen_hashes:
                matched_existing = seen_hashes[c_hash]
            else:
                # 4. Fallback check
                fb_key = compute_fallback_key(post)
                if fb_key in seen_fallbacks:
                    matched_existing = seen_fallbacks[fb_key]

        if matched_existing is not None:
            duplicate_count += 1
            # Merge matched queries
            for q in post.matched_queries:
                if q and q not in matched_existing.matched_queries:
                    matched_existing.matched_queries.append(q)
        else:
            # New unique post
            c_hash = compute_content_hash(post.content)
            fb_key = compute_fallback_key(post)

            if post.url:
                seen_urls[post.url] = post
            if post.id:
                seen_ids[post.id] = post
            seen_hashes[c_hash] = post
            seen_fallbacks[fb_key] = post

            unique_posts.append(post)

    stats = {
        "raw_count": len(posts),
        "unique_count": len(unique_posts),
        "duplicates_removed": duplicate_count,
    }
    logger.info("deduplication_completed", **stats)
    return unique_posts, stats
