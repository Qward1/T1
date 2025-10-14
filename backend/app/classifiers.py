from __future__ import annotations

import json
from typing import Any, Dict, Sequence

from .repository import fetch_categories, fetch_subcategories
from .scibox_client import get_scibox_client

CATEGORY_PROMPT = (
    "У тебя есть список основных категорий обращений клиентов банка. "
    "Выбери одну категорию из списка, которая лучше всего описывает запрос пользователя, "
    "и верни JSON вида {\"category\": \"...\", \"confidence\": 0.0}. "
    "Не добавляй другие поля."
)

SUBCATEGORY_PROMPT = (
    "У тебя есть список подкатегорий для указанной основной категории. "
    "Выбери одну подкатегорию из списка, которая лучше всего описывает запрос пользователя, "
    "и верни JSON вида {\"subcategory\": \"...\", \"confidence\": 0.0}. "
    "Не добавляй другие поля."
)

ENTITIES_PROMPT = (
    "Ты извлекаешь сущности из текста обращения. "
    "Верни строго JSON вида {\"product\": \"\", \"currency\": \"\", \"amount\": \"\", "
    "\"date\": \"\", \"problem\": \"\", \"geo\": \"\"}. "
    "Используй пустые строки, если сущность не найдена."
)

EXPECTED_ENTITY_KEYS = {"product", "currency", "amount", "date", "problem", "geo"}


def _extract_content(message: Any) -> str:
    """Аккуратно извлечь текст из ответа чат-модели."""
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, Sequence):
        parts = [
            getattr(part, "text", "")
            for part in content
            if getattr(part, "type", "") == "text"
        ]
        return "".join(parts)
    return ""


def _validate_confidence(value: Any) -> float:
    """Нормализовать confidence в диапазон [0, 1]."""
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _classify_with_choices(
    prompt: str,
    user_text: str,
    choices: Sequence[str],
    response_key: str,
) -> Dict[str, Any]:
    """Выполнить zero-shot классификацию по списку вариантов."""
    if not choices:
        return {response_key: "", "confidence": 0.0}

    options = "\n".join(f"- {choice}" for choice in choices)
    client = get_scibox_client()
    response = client.chat(
        [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Варианты:\n{options}\n\nЗапрос:\n{user_text}",
            },
        ],
        response_format={"type": "json_object"},
    )
    content = _extract_content(response)
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Модель вернула некорректный JSON: {content}") from exc

    label = str(payload.get(response_key, "") or "").strip()
    confidence = _validate_confidence(payload.get("confidence"))
    if label not in choices:
        label = ""
        confidence = 0.0
    return {response_key: label, "confidence": confidence}


def _extract_entities(text: str) -> Dict[str, str]:
    """Извлечь сущности из текста обращения."""
    client = get_scibox_client()
    response = client.chat(
        [
            {"role": "system", "content": ENTITIES_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
    )
    content = _extract_content(response)
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Модель вернула некорректный JSON при извлечении сущностей: {content}") from exc

    return {
        key: str(payload.get(key, "") or "").strip()
        for key in EXPECTED_ENTITY_KEYS
    }


def classify_and_ner(text: str) -> Dict[str, Any]:
    """Определить категорию и подкатегорию обращения и извлечь сущности."""
    if not text or not text.strip():
        raise ValueError("Текст для классификации должен быть непустой строкой.")

    categories = fetch_categories()
    main_result = _classify_with_choices(
        CATEGORY_PROMPT,
        text.strip(),
        categories,
        "category",
    )

    subcategories = fetch_subcategories(main_result["category"]) if main_result["category"] else []
    sub_result = _classify_with_choices(
        SUBCATEGORY_PROMPT,
        text.strip(),
        subcategories,
        "subcategory",
    )

    entities = _extract_entities(text.strip())

    return {
        "category": main_result["category"],
        "subcategory": sub_result["subcategory"],
        "category_confidence": main_result["confidence"],
        "subcategory_confidence": sub_result["confidence"],
        "confidence": min(main_result["confidence"], sub_result["confidence"]),
        "entities": entities,
    }

