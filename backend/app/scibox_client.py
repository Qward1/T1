from __future__ import annotations

from functools import lru_cache
from typing import Iterable, List, Sequence

from openai import OpenAI
from openai.types.chat import ChatCompletionMessage

from .settings import get_settings

DEFAULT_CHAT_MODEL = "Qwen2.5-72B-Instruct-AWQ"
DEFAULT_EMBEDDING_MODEL = "bge-m3"


class SciBoxClient:
    """Простая обёртка над OpenAI-совместимым клиентом SciBox."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        settings = get_settings()
        self._client = OpenAI(
            api_key=api_key or settings.scibox_api_key,
            base_url=base_url or settings.scibox_base_url,
        )

    def chat(
        self,
        messages: Sequence[dict[str, str]],
        *,
        model: str = DEFAULT_CHAT_MODEL,
        temperature: float = 0.0,
        **kwargs,
    ) -> ChatCompletionMessage:
        """Выполнить чат-запрос и вернуть первое сообщение из ответа."""
        response = self._client.chat.completions.create(
            model=model,
            messages=list(messages),
            temperature=temperature,
            **kwargs,
        )
        return response.choices[0].message

    def embed(
        self,
        texts: Iterable[str],
        *,
        model: str = DEFAULT_EMBEDDING_MODEL,
        **kwargs,
    ) -> List[List[float]]:
        """Сгенерировать эмбеддинги для переданных текстов."""
        payload = list(texts)
        if not payload:
            return []
        response = self._client.embeddings.create(
            model=model,
            input=payload,
            **kwargs,
        )
        return [item.embedding for item in response.data]


@lru_cache
def get_scibox_client() -> SciBoxClient:
    """Вернуть лениво инициализированный экземпляр клиента SciBox."""
    return SciBoxClient()
