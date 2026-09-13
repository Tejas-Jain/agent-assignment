from app.config import Settings
from app.agent.llm.factory import get_llm


def test_factory_returns_gemini_client():
    settings = Settings(llm_provider="gemini", gemini_api_key="x")
    llm = get_llm(settings)
    assert llm.__class__.__name__ == "GeminiClient"


def test_factory_returns_openai_client():
    settings = Settings(llm_provider="openai", openai_api_key="x")
    llm = get_llm(settings)
    assert llm.__class__.__name__ == "OpenAIClient"
