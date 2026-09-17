from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INDUSMON_", extra="ignore")

    db: Path = Path("./data/indusmon.db")
    host: str = "127.0.0.1"
    port: int = 8080
    sim_host: str = "127.0.0.1"
    sim_port: int = 5020
    poll_ms: int = 1000
    seed_demo: bool = True
    history_limit: int = 5000


settings = Settings()
