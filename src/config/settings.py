from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    use_real_llm: bool = Field(default=False, alias="USE_REAL_LLM")

    default_source_language: str = Field(default="en", alias="DEFAULT_SOURCE_LANGUAGE")
    default_target_language: str = Field(default="es", alias="DEFAULT_TARGET_LANGUAGE")
    default_document_type: str = Field(default="legal", alias="DEFAULT_DOCUMENT_TYPE")
    default_max_retries: int = Field(default=1, alias="DEFAULT_MAX_RETRIES")
    sla_seconds: int = Field(default=120, alias="SLA_SECONDS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
