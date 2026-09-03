"""Environment-based settings for the VITAVIA backend."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings loaded from environment variables or a root .env file."""

    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    google_maps_api_key: Optional[str] = None
    database_url: str = "sqlite:///./vitavia.db"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
