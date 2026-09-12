"""Typed settings and runtime configuration loaded from environment."""

import logging
from functools import lru_cache
from typing import Literal

import structlog
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation and secret masking."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys
    groq_api_key: SecretStr | None = Field(default=None, alias="GROQ_API_KEY")
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    apify_token: SecretStr | None = Field(default=None, alias="APIFY_TOKEN")
    langsmith_api_key: SecretStr | None = Field(default=None, alias="LANGSMITH_API_KEY")

    # Supabase Persistence
    supabase_url: str | None = Field(default=None, alias="NEXT_PUBLIC_SUPABASE_URL")
    supabase_anon_key: SecretStr | None = Field(default=None, alias="NEXT_PUBLIC_SUPABASE_ANON_KEY")
    supabase_service_role_key: SecretStr | None = Field(default=None, alias="SUPABASE_SERVICE_ROLE_KEY")

    # Observability
    langsmith_tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")
    langsmith_project: str = Field(default="linkedin-multi-agent", alias="LANGSMITH_PROJECT")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development", alias="APP_ENV"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # LLM Settings
    llm_model: str = Field(default="openai/gpt-oss-120b", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")

    # Limits & Guardrails
    max_search_queries: int = Field(default=20, alias="MAX_SEARCH_QUERIES")
    max_results_per_run: int = Field(default=500, alias="MAX_RESULTS_PER_RUN")
    max_deep_research_items: int = Field(default=25, alias="MAX_DEEP_RESEARCH_ITEMS")

    # Scoring Thresholds
    qualification_threshold: float = 60.0
    hot_threshold: float = 80.0

    # Scoring Weights (default to specification)
    weight_hiring_intent: float = 0.30
    weight_decision_maker: float = 0.20
    weight_company_fit: float = 0.20
    weight_freshness: float = 0.15
    weight_urgency: float = 0.10
    weight_evidence_confidence: float = 0.05

    # Apify MCP Configuration
    apify_mcp_url: str = "https://mcp.apify.com"
    apify_actor_id: str = "harvestapi/linkedin-post-search"

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key and self.groq_api_key.get_secret_value().strip())

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.get_secret_value().strip())

    @property
    def has_llm(self) -> bool:
        return self.has_groq or self.has_openai

    @property
    def has_apify(self) -> bool:
        return bool(self.apify_token and self.apify_token.get_secret_value().strip())

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and (self.supabase_service_role_key or self.supabase_anon_key))

    def get_masked_dict(self) -> dict[str, str | int | float | bool]:
        """Return safe dictionary for UI and logging without exposing secret values."""
        llm_status = "Groq Configured" if self.has_groq else ("OpenAI Configured" if self.has_openai else "Missing")
        return {
            "app_env": self.app_env,
            "log_level": self.log_level,
            "llm_model": self.llm_model,
            "llm_temperature": self.llm_temperature,
            "max_search_queries": self.max_search_queries,
            "max_results_per_run": self.max_results_per_run,
            "max_deep_research_items": self.max_deep_research_items,
            "qualification_threshold": self.qualification_threshold,
            "hot_threshold": self.hot_threshold,
            "llm_configured": llm_status,
            "openai_configured": "Configured" if self.has_openai else "Missing",
            "groq_configured": "Configured" if self.has_groq else "Missing",
            "apify_configured": "Configured" if self.has_apify else "Missing (Mock Active)",
            "supabase_configured": "Configured" if self.has_supabase else "Using SQLite (Local)",
            "langsmith_tracing": self.langsmith_tracing,
            "langsmith_project": self.langsmith_project,
            "apify_mcp_url": self.apify_mcp_url,
            "apify_actor_id": self.apify_actor_id,
        }



@lru_cache
def get_settings() -> Settings:
    """Cached singleton settings instance."""
    return Settings()


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
            if get_settings().app_env == "development"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping().get(level.upper(), 20)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
