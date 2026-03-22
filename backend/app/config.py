"""
Silent Frequency — Application Configuration

Reads settings from environment variables with sensible defaults
for local development.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Centralised config — override via environment variables or .env file."""

    # ── Database ──
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/silent_frequency"
    database_echo: bool = False  # True to log SQL statements

    # ── App ──
    app_title: str = "Silent Frequency API"
    app_version: str = "0.1.0"
    debug: bool = True
    gameplay_v2_enabled: bool = False
    cors_allowed_origins: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://26.83.101.154:3000"
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
