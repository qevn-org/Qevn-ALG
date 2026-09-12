"""Conditional routing logic for the intelligence workflow."""

from typing import Literal

import structlog

from linkedin_intelligence.config.settings import get_settings
from linkedin_intelligence.models.state import IntelligenceState

logger = structlog.get_logger(__name__)


def route_qualification(
    state: IntelligenceState,
) -> Literal["enrichment", "opportunity", "__end__"]:
    """Conditionally route based on qualification score threshold.

    Avoids expensive enrichment/decision maker steps for low-value signals.
    """
    opportunities = state.get("opportunities", [])
    if not opportunities:
        logger.info("route_qualification_no_opportunities")
        return "__end__"

    threshold = get_settings().qualification_threshold
    has_qualified = any(o.score >= threshold for o in opportunities)

    if has_qualified:
        logger.info("route_qualification_to_enrichment", threshold=threshold)
        return "enrichment"
    else:
        logger.info("route_qualification_to_low_score_finalize", threshold=threshold)
        return "opportunity"
