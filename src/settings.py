"""Shared application settings for the backend examples."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


class AppSettings(BaseSettings):
    """Environment-driven configuration shared across weekly examples."""

    app_name: str
    environment: str = Field(default="development", pattern="^(development|test|production)$")
    database_url: str
    gemini_model: str
    groq_model: str
    jwt_secret: str
    logfire_service_name: str
    groq_api_key: str
    google_api_key: str

    model_config = SettingsConfigDict(
        env_file=_ENV_PATH,
        extra="ignore",
    )
