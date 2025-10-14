from __future__ import annotations

import json
from typing import Any, Dict, Sequence

from .scibox_client import get_scibox_client

SYSTEM_PROMPT = (
    "Ты классификатор обращений клиентов банка. "
    "Проанализируй входящий текст и верни строго JSON без пояснений "
    'в следующем формате: {"category": "...", "subcategory": "...", '
    '"confidence": 0.0, "entities": {"product": "", "currency": "", '
    '"amount": "", "date": "", "problem": "", "geo": ""}}.\n\n'
    "Требования:\n"
    "- Указывай confidence числом от 0 до 1.\n"
    "- Если значение для сущности отсутствует, используй пустую строку.\n"
    "- Не добавляй комментариев, разметки или пояснений."
)

EXPECTED_ENTITY_KEYS = {"product", "currency", "amount", "date", "problem", "geo"}


def _validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure the payload matches the required schema."""
    for key in ("category", "subcategory"):
        payload[key] = str(payload.get(key, "")).strip()

    try:
        confidence = float(payload.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    payload["confidence"] = max(0.0, min(1.0, confidence))

    entities = payload.get("entities", {}) or {}
    payload["entities"] = {
        key: str(entities.get(key, "") or "").strip()
        for key in EXPECTED_ENTITY_KEYS
    }

    return payload


def _extract_content(message: Any) -> str:
    """Safely extract text content from a chat completion message."""
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


def classify_and_ner(text: str) -> Dict[str, Any]:
    """
    Classify the input text and extract entities using the SciBox LLM.
    """
    if not text or not text.strip():
        raise ValueError("Text for classification must be a non-empty string.")

    client = get_scibox_client()
    response = client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text.strip()},
        ],
        response_format={"type": "json_object"},
    )

    content = _extract_content(response)
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Classifier returned invalid JSON: {content}") from exc

    return _validate_payload(payload)
