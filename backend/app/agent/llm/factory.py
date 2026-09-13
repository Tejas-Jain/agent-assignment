from app.agent.llm.gemini_client import GeminiClient
from app.agent.llm.openai_client import OpenAIClient
from app.config import Settings


def get_llm(settings: Settings):
    if settings.llm_provider == "gemini":
        return GeminiClient(settings)
    return OpenAIClient(settings)
