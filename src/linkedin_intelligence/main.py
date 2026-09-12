"""Main entrypoint exporting compiled graph for LangGraph CLI and execution."""

import asyncio
import uuid

import structlog

from linkedin_intelligence.config.settings import setup_logging
from linkedin_intelligence.graph.builder import graph
from linkedin_intelligence.models.state import IntelligenceState

setup_logging()
logger = structlog.get_logger(__name__)


async def run_discovery(user_prompt: str) -> IntelligenceState:
    """Execute end-to-end intelligence discovery for a user prompt."""
    req_id = f"req-{uuid.uuid4().hex[:8]}"
    initial_state: IntelligenceState = {
        "request_id": req_id,
        "user_request": user_prompt,
        "raw_results": [],
        "normalized_posts": [],
        "signals": [],
        "companies": [],
        "contacts": [],
        "opportunities": [],
        "selected_opportunity_ids": [],
        "errors": [],
        "warnings": [],
        "metrics": {},
        "agent_events": [],
    }

    logger.info("starting_intelligence_discovery", request_id=req_id, prompt=user_prompt[:60])
    result = await graph.ainvoke(initial_state)
    logger.info("completed_intelligence_discovery", request_id=req_id)
    return result


if __name__ == "__main__":
    prompt = (
        "Find companies currently hiring backend engineers in India during the last 7 days "
        "where a CTO, founder, VP Engineering, or Head of Talent appears relevant."
    )
    res = asyncio.run(run_discovery(prompt))
    print(f"Discovered {len(res.get('opportunities', []))} opportunities:")
    for opp in res.get("opportunities", []):
        print(f"[{opp.temperature}] {opp.company_name} - Score: {opp.score} - Action: {opp.recommended_action}")
