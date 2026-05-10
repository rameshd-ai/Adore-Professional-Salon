from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _default_database_url() -> str:
    """File DB under backend/ so uvicorn works without a local Postgres user `glamr`."""
    return "sqlite:///" + (_BACKEND_ROOT / "glamr.db").resolve().as_posix()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(default_factory=_default_database_url)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost,http://127.0.0.1"
    admin_username: str = "apsadmin"
    admin_password: str = "Google@2610"
    session_secret: str = "change-me-in-production-use-long-random-string"
    upload_dir: str = str(_BACKEND_ROOT / "uploads")
    spa_dist: str = Field(
        default="",
        description="Path to Vite dist folder; empty uses ../frontend/dist relative to backend.",
    )
    # Set DEBUG=1 in .env to return exception details on /api/* 500 responses.
    debug: bool = False
    # If true, skip Essence remote catalog sync entirely (hair/skin prices stay DB-only).
    skip_essence_catalog_sync: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
