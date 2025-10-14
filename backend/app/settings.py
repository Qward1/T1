from functools import lru_cache
from pathlib import Path

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из переменных окружения."""

    scibox_api_key: str = Field(..., env="SCIBOX_API_KEY")
    scibox_base_url: str = Field(..., env="SCIBOX_BASE_URL")
    faq_path: Path = Field(..., env="FAQ_PATH")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def faq_source_path(self) -> Path:
        """Вернуть абсолютный путь к Excel-файлу с FAQ."""
        return self.faq_path.expanduser().resolve()


@lru_cache
def get_settings() -> Settings:
    """Получить кешированные настройки приложения.

    Raises:
        RuntimeError: если конфигурация отсутствует или заполнена некорректно.
    """
    try:
        settings = Settings()
    except ValidationError as exc:
        errors = ", ".join(
            f"{'.'.join(err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise RuntimeError(f"Invalid application configuration: {errors}") from exc
    return settings
