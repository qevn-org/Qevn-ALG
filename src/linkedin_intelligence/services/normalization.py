"""Deterministic normalization service for raw LinkedIn post data."""

import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from linkedin_intelligence.models.linkedin import LinkedInPost


def canonicalize_url(url: str | None) -> str | None:
    """Strip tracking parameters and normalize LinkedIn post URLs.

    Removes trk, trackingId, utm_*, ref, etc.
    """
    if not url or not isinstance(url, str):
        return None

    url = url.strip()
    if not url:
        return None

    try:
        parsed = urlparse(url)
        # Keep path without trailing slash
        path = parsed.path.rstrip("/")
        # Filter out tracking query params
        query_params = parse_qs(parsed.query)
        allowed_params = {}
        for k, v in query_params.items():
            k_lower = k.lower()
            if not (
                k_lower.startswith("utm_")
                or k_lower in ("trk", "trackingid", "ref", "context", "midtoken", "ek")
            ):
                allowed_params[k] = v

        clean_query = urlencode(allowed_params, doseq=True)
        canonical = urlunparse(
            (
                parsed.scheme or "https",
                parsed.netloc.lower(),
                path,
                "",
                clean_query,
                "",
            )
        )
        return canonical
    except Exception:
        return url.strip()


def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of normalized text."""
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def parse_timestamp(val: Any) -> str:
    """Format timestamp value to ISO-8601 string or readable string."""
    if isinstance(val, dict):
        if val.get("postedAgoText"):
            return str(val["postedAgoText"])
        if val.get("date"):
            return str(val["date"])
        if val.get("timestamp"):
            ts = val["timestamp"]
            if ts > 1e11:
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    elif isinstance(val, (int, float)):
        # Epoch seconds or milliseconds
        if val > 1e11:  # ms
            val = val / 1000.0
        return datetime.fromtimestamp(val, tz=timezone.utc).isoformat()
    elif isinstance(val, str) and val.strip():
        # Check standard ISO or return as string
        return val.strip()
    return datetime.now(timezone.utc).isoformat()


def extract_company_from_headline(headline: str | None) -> str | None:
    """Extract company name heuristics from author headline if available."""
    if not headline:
        return None
    # Patterns like "Engineer at Acme", "Founder @ Acme", "Tech Lead | Acme"
    patterns = [
        r"(?:at|@)\s+([A-Za-z0-9\s&.,'-]+?)(?:\s*[|•\-,]|$)",
        r"(?:building|CTO at|Founder at)\s+([A-Za-z0-9\s&.,'-]+?)(?:\s*[|•\-,]|$)",
    ]
    for pattern in patterns:
        m = re.search(pattern, headline, re.IGNORECASE)
        if m:
            comp = m.group(1).strip()
            if len(comp) > 1 and len(comp) < 50:
                return comp
    return None


def extract_company_from_content(content: str) -> str | None:
    """Extract company/practice name heuristics from post body text."""
    if not content:
        return None
    patterns = [
        r"(?:at|@)\s+([A-Z][A-Za-z0-9\s&.,'-]{2,35}?)(?:\s*(?:is\s+hiring|is\s+looking|[.\n,!•]|$))",
        r"([A-Z][A-Za-z0-9\s&.,'-]{2,35}?)\s+is\s+(?:looking\s+for|hiring|urgently\s+hiring)",
        r"(?:join\s+(?:the|our)\s+team\s+at)\s+([A-Z][A-Za-z0-9\s&.,'-]{2,35}?)(?:\s*[.\n,!•]|$)",
        r"(?:Hospital|Clinic|Dental|Health|Care|Tech)\s+([A-Za-z0-9\s&.,'-]{2,30}?)",
    ]
    for pattern in patterns:
        m = re.search(pattern, content)
        if m:
            comp = m.group(1).strip()
            # Filter out non-names
            if len(comp) > 2 and comp.lower() not in ("our", "the", "a", "an", "this", "we", "immediate", "looking"):
                return comp
    return None


def normalize_post(raw: dict, matched_query: str = "") -> LinkedInPost:
    """Deterministically convert raw scraper output into typed LinkedInPost."""
    raw_id = str(
        raw.get("id")
        or raw.get("urn")
        or raw.get("postUrn")
        or raw.get("postId")
        or ""
    ).strip()

    raw_url = raw.get("linkedinUrl") or raw.get("postUrl") or raw.get("url") or raw.get("link")
    canonical_url = canonicalize_url(raw_url)

    content = str(
        raw.get("text")
        or raw.get("content")
        or raw.get("postContent")
        or raw.get("description")
        or ""
    ).strip()

    # Author info
    author = raw.get("author") or {}
    if isinstance(author, dict):
        author_name = author.get("name") or author.get("fullName") or raw.get("authorName")
        author_headline = author.get("headline") or author.get("info") or raw.get("authorHeadline")
        author_profile_url = canonicalize_url(
            author.get("linkedinUrl") or author.get("profileUrl") or author.get("url") or raw.get("authorProfileUrl")
        )
        company_name = author.get("companyName") or raw.get("companyName")
        company_id = author.get("companyIdentifier") or raw.get("companyIdentifier")
    else:
        author_name = raw.get("authorName") or (str(author) if author else None)
        author_headline = raw.get("authorHeadline")
        author_profile_url = canonicalize_url(raw.get("authorProfileUrl") or raw.get("authorUrl"))
        company_name = raw.get("companyName") or raw.get("company")
        company_id = raw.get("companyIdentifier") or raw.get("companyPublicIdentifier")

    if not company_name and author_headline:
        company_name = extract_company_from_headline(author_headline)

    if not company_name and content:
        company_name = extract_company_from_content(content)

    if not company_name and author_name:
        company_name = f"{author_name}'s Practice / Org"

    published_at = parse_timestamp(
        raw.get("publishedAt")
        or raw.get("postedAt")
        or raw.get("date")
        or raw.get("time")
        or raw.get("timestamp")
    )

    # Derive deterministic ID if missing
    if not raw_id:
        if canonical_url:
            raw_id = "url-" + hashlib.md5(canonical_url.encode()).hexdigest()[:12]
        else:
            raw_id = "txt-" + compute_content_hash(content)

    queries = [matched_query] if matched_query else []

    return LinkedInPost(
        id=raw_id,
        url=canonical_url,
        content=content,
        author_name=author_name,
        author_profile_url=author_profile_url,
        author_headline=author_headline,
        company_name=company_name,
        company_identifier=company_id,
        published_at=published_at,
        source="linkedin",
        matched_queries=queries,
        raw_data=raw,
    )


def normalize_results(
    raw_items: list[dict], matched_query: str = ""
) -> list[LinkedInPost]:
    """Normalize a batch of raw scraper outputs."""
    normalized: list[LinkedInPost] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        try:
            post = normalize_post(item, matched_query=matched_query)
            if post.content:  # Discard empty posts
                normalized.append(post)
        except Exception:
            # Safe skip of malformed items
            continue
    return normalized
