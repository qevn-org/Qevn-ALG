"""Unit tests for deterministic normalization service."""

from linkedin_intelligence.services.normalization import (
    canonicalize_url,
    compute_content_hash,
    extract_company_from_headline,
    normalize_post,
    normalize_results,
)


def test_canonicalize_url():
    raw_url = "https://www.linkedin.com/feed/update/urn:li:activity:7198234101/?trk=feed-detail_main-feed-card&utm_source=share&midToken=xyz"
    clean = canonicalize_url(raw_url)
    assert clean == "https://www.linkedin.com/feed/update/urn:li:activity:7198234101"
    assert "trk=" not in clean
    assert "utm_source" not in clean


def test_compute_content_hash():
    h1 = compute_content_hash("We are hiring backend engineers!   ")
    h2 = compute_content_hash("we   are HIRING backend engineers!")
    assert h1 == h2


def test_extract_company_from_headline():
    hl = "VP of Engineering at RazorFlow | Ex-Uber"
    comp = extract_company_from_headline(hl)
    assert comp == "RazorFlow"

    hl2 = "Founder @ ZetaScale"
    comp2 = extract_company_from_headline(hl2)
    assert comp2 == "ZetaScale"


def test_normalize_post():
    raw = {
        "id": "urn:li:activity:999",
        "postUrl": "https://www.linkedin.com/feed/update/urn:li:activity:999?trk=some_trk",
        "text": "Looking for Go and Python developers in Pune.",
        "author": {
            "name": "Jane Doe",
            "headline": "Engineering Manager at PuneTech",
            "profileUrl": "https://www.linkedin.com/in/janedoe/?trk=abc",
        },
        "publishedAt": "2026-09-10T10:00:00Z",
    }
    post = normalize_post(raw, matched_query="hiring python developers")
    assert post.id == "urn:li:activity:999"
    assert post.author_name == "Jane Doe"
    assert post.company_name == "PuneTech"
    assert "trk=" not in (post.url or "")
    assert post.matched_queries == ["hiring python developers"]


def test_normalize_results_skips_empty():
    raw_items = [
        {"id": "1", "text": "Hiring engineer!"},
        {"id": "2", "text": ""},
        "not a dict",
    ]
    posts = normalize_results(raw_items)  # type: ignore[arg-type]
    assert len(posts) == 1
    assert posts[0].id == "1"
