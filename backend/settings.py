from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str | None) -> Tuple[str, ...]:
    if not value:
        return tuple()
    return tuple(
        part.strip()
        for part in value.split(",")
        if part.strip()
    )


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    scibox_api_key: str = Field(..., alias="SCIBOX_API_KEY")
    scibox_base_url: str = Field(..., alias="SCIBOX_BASE_URL")

    faq_path: Optional[Path] = Field(None, alias="FAQ_PATH")

    admin_token: Optional[str] = Field(None, alias="ADMIN_TOKEN")
    frontend_origins_raw: Optional[str] = Field(None, alias="FRONTEND_ORIGINS")

    rate_limit_window_seconds: int = Field(600, alias="RATE_LIMIT_WINDOW")
    rate_limit_max_requests: int = Field(10, alias="RATE_LIMIT_MAX_REQUESTS")
    warmup_enabled: bool = Field(False, alias="WARMUP")
    max_request_bytes: int = Field(100_000, alias="MAX_REQUEST_BYTES")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def faq_source_path(self) -> Optional[Path]:
        return self.faq_path.expanduser().resolve() if self.faq_path else None

    @property
    def frontend_origins(self) -> Tuple[str, ...]:
        origins = _split_csv(self.frontend_origins_raw)
        return origins if origins else ("*",)


@lru_cache
def get_settings() -> Settings:
    """Return shared Settings instance or raise a meaningful error."""

    try:
        settings = Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        errors = ", ".join(
            f"{'.'.join(str(x) for x in err.get('loc', ())) or '?'}: {err.get('msg', 'unknown')}"
            for err in exc.errors()
        )
        raise RuntimeError(f"Invalid application configuration: {errors}") from exc
    return settings
