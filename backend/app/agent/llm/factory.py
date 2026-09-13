from app.agent.llm.gemini_client import GeminiProvider
from app.agent.llm.openai_client import OpenAIProvider
from app.agent.llm.base import LLMProvider
from app.config import Settings


def get_llm(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "gemini":
        return GeminiProvider(settings)
    return OpenAIProvider(settings)
