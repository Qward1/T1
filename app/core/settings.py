from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    scibox_api_key: str = Field(..., alias="SCIBOX_API_KEY")
    scibox_base_url: str = Field(..., alias="SCIBOX_BASE_URL")
    faq_path: str = Field(..., alias="FAQ_PATH")
    database_url: str = Field("sqlite:///data/app.db", alias="DATABASE_URL")
    embeddings_path: str = Field("data/faq_embeddings.npy", alias="EMBEDDINGS_PATH")
    stats_db_path: str = Field("data/stats.db", alias="STATS_DB_PATH")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]

