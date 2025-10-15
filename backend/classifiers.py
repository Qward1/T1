from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from openai import APIConnectionError, RateLimitError

from .repository import fetch_all_templates, fetch_template_embeddings
from .scibox_client import DEFAULT_EMBEDDING_MODEL, get_scibox_client
from .text_utils import normalize_text

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.35
MAX_TOP_MATCHES = 5

# -- Product detection -------------------------------------------------------

PRODUCT_LIST = [
    "MORE",
    "more",
    "Форсаж",
    "форсаж",
    "Комплимент",
    "комплимент",
    "Signature",
    "signature",
    "Infinite",
    "infinite",
    "PLAT/ON",
    "plat/on",
    "Портмоне 2.0",
    "портмоне 2.0",
    "Отличник",
    "отличник",
    "ЧЕРЕПАХА",
    "черепаха",
    "карта КСТАТИ",
    "карта кстати",
    "кредит дальше",
    "кредит легко",
    "Старт",
    "старт",
]

_PRODUCT_MAP: Dict[str, str] = {item.casefold(): item for item in PRODUCT_LIST if item}


def detect_products(text: str) -> List[str]:
    """Находит упоминания известных продуктов в запросе клиента."""
    if not text:
        return []
    normalized = text.casefold()
    seen: set[str] = set()
    matches: List[str] = []
    for key, label in _PRODUCT_MAP.items():
        if key and key in normalized and key not in seen:
            seen.add(key)
            matches.append(label)
    return matches



# -- Шаблонные вопросы ------------------------------------------------------

@dataclass(frozen=True)
class TemplateEntry:
    id: int
    question: str
    normalized_question: str
    category: str
    subcategory: str
    answer: str


@lru_cache(maxsize=1)
def _load_templates() -> Tuple[TemplateEntry, ...]:
    rows = fetch_all_templates()
    entries: List[TemplateEntry] = []
    for row in rows:
        question = (row.get("question") or "").strip()
        category = (row.get("category") or "").strip()
        subcategory = (row.get("subcategory") or "").strip()
        answer = row.get("answer") or ""
        if not question or not category or not subcategory:
            continue
        normalized = normalize_text(question)
        if not normalized:
            continue
        entries.append(
            TemplateEntry(
                id=int(row["id"]),
                question=question,
                normalized_question=normalized,
                category=category,
                subcategory=subcategory,
                answer=answer,
            )
        )

    if not entries:
        raise RuntimeError("Template library is empty.")

    return tuple(entries)


_TEMPLATE_CACHE: Optional[Tuple[Tuple[TemplateEntry, ...], np.ndarray]] = None


def refresh_template_cache() -> None:
    """Clear cached template embeddings (call after rebuilding FAQ data)."""
    global _TEMPLATE_CACHE
    _TEMPLATE_CACHE = None


def _get_template_data() -> Tuple[Tuple[TemplateEntry, ...], np.ndarray]:
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is None:
        entries = _load_templates()
        ids = [entry.id for entry in entries]
        embedding_map = fetch_template_embeddings(ids)
        if len(embedding_map) != len(entries):
            missing = sorted({entry.id for entry in entries} - set(embedding_map))
            raise RuntimeError(f"Missing embeddings for template ids: {missing}")
        vectors = np.vstack([embedding_map[entry.id] for entry in entries]).astype(np.float32)
        _TEMPLATE_CACHE = (entries, vectors)
    return _TEMPLATE_CACHE


def _encode_query(text: str) -> Tuple[np.ndarray, str]:
    normalized = normalize_text(text)
    if not normalized:
        raise RuntimeError("Failed to normalize query.")
    client = get_scibox_client()
    try:
        [vector] = client.embed([normalized], model=DEFAULT_EMBEDDING_MODEL)
    except (RateLimitError, APIConnectionError) as exc:
        logger.warning("Embedding request failed: %s", exc)
        raise RuntimeError("Embedding service unavailable.") from exc
    embedding = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(embedding))
    if norm == 0:
        raise RuntimeError("Failed to obtain embedding for query.")
    return embedding / norm, normalized


def _match_template(
    text: str,
) -> Tuple[Optional[TemplateEntry], float, List[Tuple[TemplateEntry, float]], str]:
    try:
        entries, matrix = _get_template_data()
    except RuntimeError as exc:
        logger.warning("Template cache unavailable: %s", exc)
        return None, 0.0, [], normalize_text(text)

    try:
        query_vector, normalized_query = _encode_query(text)
    except RuntimeError as exc:
        logger.warning("Failed to encode query: %s", exc)
        return None, 0.0, [], normalize_text(text)

    if matrix.size == 0:
        return None, 0.0, [], normalized_query

    scores = matrix @ query_vector
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])

    top_indices = np.argsort(-scores)[: MAX_TOP_MATCHES or len(entries)]
    top_matches = [(entries[idx], float(scores[idx])) for idx in top_indices]

    best_entry = entries[best_idx] if entries else None
    return best_entry, best_score, top_matches, normalized_query


# -- Извлечение сущностей ---------------------------------------------------

EXPECTED_ENTITY_KEYS = {"product", "currency", "amount", "date", "problem", "geo"}

_AMOUNT_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[ \u00A0\u202F]?\d{3})*(?:[.,]\d{1,2})?)(?!\d)")
_DATE_RE = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b")
_GEO_RE = re.compile(r"\b(?:г\.|город)\s*([A-ZА-ЯЁ][\w\-]*)", re.IGNORECASE)
_GEO_IN_RE = re.compile(r"\bв\s+([A-ZА-ЯЁ][\w\-]*)", re.IGNORECASE)
_CURRENCY_PATTERNS: Tuple[Tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:руб(?:л[еяй]?)?|р\.|₽)\b", re.IGNORECASE), "RUB"),
    (re.compile(r"\b(?:usd|доллар(?:ов)?|\$)\b", re.IGNORECASE), "USD"),
    (re.compile(r"\b(?:eur|евро|€)\b", re.IGNORECASE), "EUR"),
    (re.compile(r"\b(?:тенге|₸|kzt)\b", re.IGNORECASE), "KZT"),
)


def _fallback_entities(text: str) -> Dict[str, str]:
    """Best-effort local entity extraction used when the remote model is unavailable."""
    cleaned = (text or "").strip()
    if not cleaned:
        return {key: "" for key in EXPECTED_ENTITY_KEYS}

    normalized = cleaned.replace("\u00A0", " ").replace("\u202F", " ")

    amount = ""
    amount_match = _AMOUNT_RE.search(normalized)
    if amount_match:
        amount = re.sub(r"[ \u00A0\u202F]", "", amount_match.group(1))

    currency = ""
    for pattern, label in _CURRENCY_PATTERNS:
        if pattern.search(cleaned):
            currency = label
            break

    date = ""
    date_match = _DATE_RE.search(cleaned)
    if date_match:
        date = date_match.group(0)

    geo = ""
    geo_match = _GEO_RE.search(cleaned)
    if geo_match:
        geo = geo_match.group(1)
    else:
        geo_match = _GEO_IN_RE.search(cleaned)
        if geo_match:
            geo = geo_match.group(1)

    first_sentence = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)[0]
    problem = first_sentence[:160]
    if len(first_sentence) > 160:
        problem = problem.rstrip() + "..."

    return {
        "product": "",
        "currency": currency,
        "amount": amount,
        "date": date,
        "problem": problem,
        "geo": geo,
    }


def _extract_entities(text: str) -> Dict[str, str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return {key: "" for key in EXPECTED_ENTITY_KEYS}
    return _fallback_entities(cleaned)


# -- Основная точка входа ---------------------------------------------------

def classify_and_ner(text: str) -> Dict[str, Any]:
    if not text or not text.strip():
        raise ValueError("Text for classification must be a non-empty string.")

    cleaned_text = text.strip()
    products = detect_products(cleaned_text)

    best_entry, raw_score, top_matches, normalized_query = _match_template(cleaned_text)
    confidence = max(raw_score, 0.0)
    below_threshold = raw_score < SIMILARITY_THRESHOLD

    category = best_entry.category if best_entry else None
    subcategory = best_entry.subcategory if best_entry else None

    entities = _extract_entities(cleaned_text)
    if not entities.get("product") and products:
        entities["product"] = ", ".join(products)

    top_matches_payload = [
        {
            "id": match.id,
            "question": match.question,
            "category": match.category,
            "subcategory": match.subcategory,
            "score": max(score, 0.0),
        }
        for match, score in top_matches
    ]

    return {
        "category": category,
        "subcategory": subcategory,
        "category_confidence": confidence,
        "subcategory_confidence": confidence,
        "confidence": confidence,
        "matched_template_question": best_entry.question if best_entry else None,
        "matched_template_id": best_entry.id if best_entry else None,
        "matched_template_score": confidence,
        "matched_template_raw_score": raw_score,
        "below_threshold": below_threshold,
        "entities": entities,
        "products": products,
        "classification_details": {
            "normalized_query": normalized_query,
            "similarity_threshold": SIMILARITY_THRESHOLD,
            "top_matches": top_matches_payload,
        },
    }
