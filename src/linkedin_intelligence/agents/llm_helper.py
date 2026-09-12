"""LLM factory and prompt loader helper with robust fallbacks."""

import json
from pathlib import Path
from typing import Any

import structlog
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from linkedin_intelligence.config.settings import Settings, get_settings

logger = structlog.get_logger(__name__)


def load_prompt(filename: str) -> str:
    """Load prompt template text from prompts directory."""
    prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
    prompt_path = prompts_dir / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()
    return ""


def get_llm(settings: Settings | None = None) -> BaseChatModel | None:
    """Get ChatGroq or ChatOpenAI instance based on configured credentials."""
    settings = settings or get_settings()

    # Prioritize Groq if configured
    if settings.has_groq:
        try:
            return ChatGroq(
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                api_key=settings.groq_api_key.get_secret_value(),  # type: ignore[union-attr]
            )
        except Exception as e:
            logger.error("groq_init_failed", error=str(e))

    # Fall back to OpenAI if configured
    if settings.has_openai:
        try:
            return ChatOpenAI(
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                api_key=settings.openai_api_key.get_secret_value(),  # type: ignore[union-attr]
            )
        except Exception as e:
            logger.error("openai_init_failed", error=str(e))

    return None


async def run_structured_llm(
    prompt_file: str,
    user_content: str,
    default_fallback: Any,
    settings: Settings | None = None,
) -> Any:
    """Run an LLM call with system prompt, parsing JSON output, with fallback."""
    llm = get_llm(settings)
    if not llm:
        return default_fallback

    system_prompt = load_prompt(prompt_file)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    try:
        response = await llm.ainvoke(messages)
        text = response.content
        if isinstance(text, list):
            text = " ".join(str(item) for item in text)

        # Extract JSON substring
        text = text.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()

        return json.loads(text)
    except Exception as e:
        logger.warning("llm_parse_failed_using_fallback", prompt=prompt_file, error=str(e))
        return default_fallback
