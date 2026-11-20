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
    cors_origins: list[str] = ["http://localhost:3000"]

    # City config
    city_name: str = "Goa, India"
    city_center_lat: float = 15.4909
    city_center_lng: float = 73.8278
    city_currency: str = "INR"
    city_emergency_number: str = "112"

    # Feature flags
    is_demo_data: bool = True
    max_radius_km: float = 10.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
