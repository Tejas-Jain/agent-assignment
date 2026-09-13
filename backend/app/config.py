from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    max_tool_iterations: int = 10

    def validate_provider(self) -> None:
        if not self.gemini_api_key.strip():
            raise ValueError("GEMINI_API_KEY is required")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_settings(settings: Settings | None = None) -> None:
    s = settings or get_settings()
    s.validate_provider()
