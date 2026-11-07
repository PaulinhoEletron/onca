"""Configuração lida do ambiente e do arquivo .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://onca:onca@localhost:5433/onca"
    embedding_model: str = "intfloat/multilingual-e5-small"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None


def get_settings() -> Settings:
    return Settings()
