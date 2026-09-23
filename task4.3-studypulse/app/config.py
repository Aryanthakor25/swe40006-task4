"""Config is read from environment variables so the same image works locally
and on EC2 without rebuilding."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_title: str
    app_env: str
    app_version: str
    redis_host: str
    redis_port: int
    redis_db: int
    log_level: str


def load_settings() -> Settings:
    return Settings(
        app_title=os.getenv("APP_TITLE", "StudyPulse"),
        app_env=os.getenv("APP_ENV", "development"),
        app_version=os.getenv("APP_VERSION", "1.0.0"),
        redis_host=os.getenv("REDIS_HOST", ""),  # empty = use in-memory store
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        redis_db=int(os.getenv("REDIS_DB", "0")),
        log_level=os.getenv("LOG_LEVEL", "info").upper(),
    )
