from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence

from .repository import fetch_categories, fetch_subcategories
from .scibox_client import get_scibox_client

PRODUCT_LIST = [
    "MORE",
    "more",
    "\u0424\u043e\u0440\u0441\u0430\u0436",
    "\u0444\u043e\u0440\u0441\u0430\u0436",
    "\u041a\u043e\u043c\u043f\u043b\u0438\u043c\u0435\u043d\u0442",
    "\u043a\u043e\u043c\u043f\u043b\u0438\u043c\u0435\u043d\u0442",
    "Signature",
    "signature",
    "Infinite",
    "infinite",
    "PLAT/ON",
    "plat/on",
    "\u041f\u043e\u0440\u0442\u043c\u043e\u043d\u0435 2.0",
    "\u043f\u043e\u0440\u0442\u043c\u043e\u043d\u0435 2.0",
    "\u041e\u0442\u043b\u0438\u0447\u043d\u0438\u043a",
    "\u043e\u0442\u043b\u0438\u0447\u043d\u0438\u043a",
    "\u0427\u0415\u0420\u0415\u041f\u0410\u0425\u0410",
    "\u0447\u0435\u0440\u0435\u043f\u0430\u0445\u0430",
    "\u041a\u0421\u0422\u0410\u0422\u0418",
    "\u043a\u0441\u0442\u0430\u0442\u0438",
    "\u043a\u0440\u0435\u0434\u0438\u0442 \u0434\u0430\u043b\u044c\u0448\u0435",
    "\u043a\u0440\u0435\u0434\u0438\u0442 \u043b\u0435\u0433\u043a\u043e",
    "\u0421\u0442\u0430\u0440\u0442",
    "\u0441\u0442\u0430\u0440\u0442",
]

_PRODUCT_MAP: Dict[str, str] = {item.casefold(): item for item in PRODUCT_LIST if item}

CATEGORY_PROMPT = (
    "You must classify the customer request into the most relevant main category. "
    "Use only the provided options and consider the mentioned products."
)

SUBCATEGORY_PROMPT = (
    "Select the most relevant subcategory inside the chosen category. "
    "Use the provided subcategory list and the detected products."
)

ENTITIES_PROMPT = (
    "Extract entities from the customer request. "
    "Return strict JSON of the form {\"product\": \"\", \"currency\": \"\", \"amount\": \"\", "
    "\"date\": \"\", \"problem\": \"\", \"geo\": \"\"}. "
    "Use empty strings when an entity is not present."
)

EXPECTED_ENTITY_KEYS = {"product", "currency", "amount", "date", "problem", "geo"}


def _extract_content(message: Any) -> str:
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
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _detect_products(text: str) -> List[str]:
    normalized = text.casefold()
    seen: set[str] = set()
    matches: List[str] = []
    for key, label in _PRODUCT_MAP.items():
        if key and key in normalized and key not in seen:
            seen.add(key)
            matches.append(label)
    return matches


def _classify_with_choices(
    prompt: str,
    user_text: str,
    choices: Sequence[str],
    response_key: str,
    products: Sequence[str],
) -> Dict[str, Any]:
    if not choices:
        return {response_key: "", "confidence": 0.0}

    options = "\n".join(f"- {choice}" for choice in choices)
    products_block = (
        "Mentioned products:\n" + "\n".join(f"- {name}" for name in products)
        if products
        else "Mentioned products: none."
    )

    client = get_scibox_client()
    response = client.chat(
        [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    f"Options:\n{options}\n\n{products_block}\n\n"
                    f"Customer request:\n{user_text}"
                ),
            },
        ],
        response_format={"type": "json_object"},
    )
    content = _extract_content(response)
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Classifier returned invalid JSON: {content}") from exc

    label = str(payload.get(response_key, "") or "").strip()
    confidence = _validate_confidence(payload.get("confidence"))
    if label not in choices:
        label = ""
        confidence = 0.0
    return {response_key: label, "confidence": confidence}


def _extract_entities(text: str) -> Dict[str, str]:
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
        raise RuntimeError(f"Entity extractor returned invalid JSON: {content}") from exc

    return {
        key: str(payload.get(key, "") or "").strip()
        for key in EXPECTED_ENTITY_KEYS
    }


def classify_and_ner(text: str) -> Dict[str, Any]:
    if not text or not text.strip():
        raise ValueError("Text for classification must be a non-empty string.")

    products = _detect_products(text)

    categories = fetch_categories()
    main_result = _classify_with_choices(
        CATEGORY_PROMPT,
        text.strip(),
        categories,
        "category",
        products,
    )

    subcategories = fetch_subcategories(main_result["category"]) if main_result["category"] else []
    sub_result = _classify_with_choices(
        SUBCATEGORY_PROMPT,
        text.strip(),
        subcategories,
        "subcategory",
        products,
    )

    entities = _extract_entities(text.strip())
    if not entities.get("product") and products:
        entities["product"] = ", ".join(products)

    return {
        "category": main_result["category"],
        "subcategory": sub_result["subcategory"],
        "category_confidence": main_result["confidence"],
        "subcategory_confidence": sub_result["confidence"],
        "confidence": min(main_result["confidence"], sub_result["confidence"]),
        "entities": entities,
        "products": products,
    }
