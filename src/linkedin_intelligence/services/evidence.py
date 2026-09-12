"""Evidence tracing and audit service linking opportunities to source posts."""

from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.models.opportunities import Opportunity
from linkedin_intelligence.models.signals import Signal


class EvidenceService:
    """Manages traceability between raw posts, extracted signals, and opportunities."""

    def __init__(self, posts: list[LinkedInPost]):
        self._post_map: dict[str, LinkedInPost] = {p.id: p for p in posts}

    def get_post(self, post_id: str) -> LinkedInPost | None:
        return self._post_map.get(post_id)

    def get_posts_for_ids(self, post_ids: list[str]) -> list[LinkedInPost]:
        return [self._post_map[pid] for pid in post_ids if pid in self._post_map]

    def build_evidence_dossier(
        self, opportunity: Opportunity, signals: list[Signal]
    ) -> dict:
        """Create structured audit trail for an opportunity."""
        matching_signals = [
            s for s in signals if s.company_name.lower() == opportunity.company_name.lower()
        ]
        evidence_posts = self.get_posts_for_ids(opportunity.evidence_post_ids)

        return {
            "opportunity_id": opportunity.id,
            "company_name": opportunity.company_name,
            "temperature": opportunity.temperature,
            "score": opportunity.score,
            "signals": [s.model_dump() for s in matching_signals],
            "posts_count": len(evidence_posts),
            "posts": [
                {
                    "id": p.id,
                    "url": p.url,
                    "author_name": p.author_name,
                    "author_headline": p.author_headline,
                    "published_at": p.published_at,
                    "content_preview": p.content_preview,
                    "matched_queries": p.matched_queries,
                }
                for p in evidence_posts
            ],
        }
