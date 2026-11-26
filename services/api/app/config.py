"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://traveldoc:traveldoc@localhost:5432/traveldoc"
    database_url_sync: str = "postgresql+psycopg2://traveldoc:traveldoc@localhost:5432/traveldoc"

    # Admin
    admin_username: str = "admin"
    admin_password: str = "changeme"
    secret_key: str = "dev-secret-key-change-in-production"

    # CORS
    cors_origins: str | list[str] = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        if isinstance(self.cors_origins, list):
            return self.cors_origins
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # City config
    city_name: str = "Goa, India"
    city_center_lat: float = 15.4909
    city_center_lng: float = 73.8278
    city_currency: str = "INR"
    city_emergency_number: str = "112"

    # Feature flags
    is_demo_data: bool = True
    max_radius_km: float = 10.0

    # OpenRouter / LLM search configuration
    llm_search_enabled: bool = True
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    openrouter_timeout_seconds: float = 25.0
    openrouter_max_retries: int = 2

    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
