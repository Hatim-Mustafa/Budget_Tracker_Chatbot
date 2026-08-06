"""Shared application settings for the backend examples."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

# pydantic-settings reads .env into the settings object only — it does NOT put the
# values into os.environ. pydantic-ai's model providers (GroqProvider, GoogleProvider)
# authenticate via os.getenv('GROQ_API_KEY') / os.getenv('GOOGLE_API_KEY'), so export
# the .env contents into the process environment too (existing env vars win).
load_dotenv(_ENV_PATH)


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
