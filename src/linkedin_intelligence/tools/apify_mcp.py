"""Apify MCP client integration using langchain-mcp-adapters."""

import structlog
from langchain_mcp_adapters.client import MultiServerMCPClient

from linkedin_intelligence.config.settings import Settings, get_settings

logger = structlog.get_logger(__name__)


class ApifyMCPManager:
    """Manages connection and tool discovery with the Apify MCP Server."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client: MultiServerMCPClient | None = None

    def is_configured(self) -> bool:
        return self.settings.has_apify

    def get_client(self) -> MultiServerMCPClient | None:
        if not self.is_configured():
            logger.warning("apify_mcp_token_not_configured")
            return None

        if self._client is None:
            token = self.settings.apify_token.get_secret_value()  # type: ignore[union-attr]
            connections = {
                "apify": {
                    "transport": "streamable_http",
                    "url": self.settings.apify_mcp_url,
                    "headers": {
                        "Authorization": f"Bearer {token}",
                    },
                    "timeout": 30.0,
                }
            }
            try:
                self._client = MultiServerMCPClient(connections=connections)  # type: ignore[arg-type]
                logger.info("apify_mcp_client_initialized", url=self.settings.apify_mcp_url)
            except Exception as e:
                logger.error("apify_mcp_init_failed", error=str(e))
                return None

        return self._client

    async def get_available_tools(self) -> list:
        client = self.get_client()
        if not client:
            return []
        try:
            tools = await client.get_tools()
            tool_names = [getattr(t, "name", str(t)) for t in tools]
            logger.info("apify_mcp_tools_discovered", count=len(tools), tools=tool_names)
            return tools
        except Exception as e:
            logger.error("apify_mcp_get_tools_failed", error=str(e))
            return []
