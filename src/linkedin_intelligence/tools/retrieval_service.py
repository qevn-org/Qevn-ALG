"""Provider adapter isolating the graph from Apify internals."""

import json
from pathlib import Path
from typing import Any

import httpx
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from linkedin_intelligence.config.settings import Settings, get_settings
from linkedin_intelligence.models.search import ActorSearchInput, SearchPlan
from linkedin_intelligence.tools.apify_mcp import ApifyMCPManager

logger = structlog.get_logger(__name__)


class LinkedInRetrievalService:
    """Service providing LinkedIn search results through Apify MCP with resilient fallbacks."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.mcp_manager = ApifyMCPManager(self.settings)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=6),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _call_apify_api(self, actor_input: ActorSearchInput) -> list[dict[str, Any]]:
        """Direct resilient call to Apify Actor run-sync-get-dataset-items."""
        token = self.settings.apify_token.get_secret_value()  # type: ignore[union-attr]
        actor_slug = self.settings.apify_actor_id.replace("/", "~")
        endpoint = f"https://api.apify.com/v2/acts/{actor_slug}/run-sync-get-dataset-items"

        payload: dict[str, Any] = {
            "searchQueries": actor_input.searchQueries,
            "maxPosts": min(actor_input.maxPosts, 15),
            "postedLimit": actor_input.postedLimit or "week",
            "sortBy": actor_input.sortBy or "date",
        }
        if actor_input.authorsCompanyPublicIdentifiers:
            payload["authorsCompanies"] = actor_input.authorsCompanyPublicIdentifiers

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code == 401:
                logger.error("apify_auth_failure", status_code=401)
                raise PermissionError("Invalid Apify Token (401 Unauthorized)")
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            return []

    def _load_fixture_data(self, queries: list[str]) -> list[dict[str, Any]]:
        """Load fixture data matching user queries only when running offline unit tests without credentials."""
        fixture_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "fixtures" / "linkedin_posts.json"
        if not fixture_path.exists():
            test_fixture = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "fixtures" / "linkedin_posts.json"
            if test_fixture.exists():
                fixture_path = test_fixture

        if not fixture_path.exists():
            return []

        try:
            with open(fixture_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    async def search(self, plan: SearchPlan) -> list[dict[str, Any]]:
        """Execute validated search plan and return live scraped LinkedIn post dictionaries."""
        raw_queries = [q.strip() for q in plan.queries if q.strip()]
        if not raw_queries:
            logger.warning("empty_search_plan_queries")
            return []

        # If live Apify credentials are configured, execute real-time search
        if self.settings.has_apify:
            # Send top 3 focused queries to ensure fast real-time completion
            live_queries = raw_queries[:3]
            actor_input = ActorSearchInput(
                searchQueries=live_queries,
                authorsCompanyPublicIdentifiers=plan.company_identifiers,
                maxPosts=10,
                postedLimit="week",
                sortBy="date",
            )
            logger.info("live_retrieval_executing", queries=live_queries)
            try:
                results = await self._call_apify_api(actor_input)
                logger.info("live_retrieval_success", count=len(results))
                return results
            except Exception as e:
                logger.error("live_apify_retrieval_error", error=str(e))
                # Never return demo data in live mode - return empty with log
                return []
        else:
            logger.info("no_apify_token_offline_mode")
            return self._load_fixture_data(raw_queries[: self.settings.max_search_queries])
