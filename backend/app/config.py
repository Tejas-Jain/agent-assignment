from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: Literal["openai", "gemini"] = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    openai_api_key: str = ""
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"
    max_tool_iterations: int = 10

    def validate_provider(self) -> None:
        if self.llm_provider == "gemini" and not self.gemini_api_key.strip():
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        if self.llm_provider == "openai" and not self.openai_api_key.strip():
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_settings(settings: Settings | None = None) -> None:
    s = settings or get_settings()
    s.validate_provider()
