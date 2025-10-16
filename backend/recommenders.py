from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from .repository import (
    fetch_all_embeddings,
    fetch_all_ids,
    fetch_ids_for_segment,
    fetch_records_by_ids,
)
from .scibox_client import get_scibox_client
from .text_utils import normalize_text

FINALIZE_PROMPT = (
    "Вы эксперт службы поддержки. "
    "Вам дан шаблон ответа и распознанные сущности. "
    "Подготовьте финальный ответ, подставив сущности, сохраняя стиль и смысл."
)


@lru_cache
def _load_embeddings() -> Tuple[np.ndarray, Dict[int, int]]:
    ids, matrix = fetch_all_embeddings()
    index = {faq_id: idx for idx, faq_id in enumerate(ids)}
    return matrix, index


def preload_embeddings() -> None:
   
    _load_embeddings()


def refresh_embeddings() -> None:
    
    _load_embeddings.cache_clear()
    _load_embeddings()

    try:
        from . import classifiers
        classifiers.refresh_template_cache()
    except Exception:
        pass

def _vectorize_query(text: str) -> np.ndarray:
    cleaned = normalize_text(text) or text.strip()
    client = get_scibox_client()
    [embedding] = client.embed([cleaned])
    vector = np.array(embedding, dtype="float32")
    norm = np.linalg.norm(vector)
    return vector if norm == 0 else vector / norm


def _boost_by_products(
    scores: np.ndarray,
    candidate_ids: Sequence[int],
    products: Sequence[str],
) -> np.ndarray:
    if not products:
        return scores

    products_lower = [product.casefold() for product in products if product]
    if not products_lower:
        return scores

    records_map = fetch_records_by_ids(candidate_ids)
    boosted = scores.copy()
    for idx, record_id in enumerate(candidate_ids):
        record = records_map.get(record_id)
        if not record:
            continue
        question_text = (record.get("question") or "").casefold()
        answer_text = (record.get("answer") or "").casefold()
        boost = 0.0
        for product in products_lower:
            if product in question_text:
                boost += 0.2
            elif product in answer_text:
                boost += 0.1
        boosted[idx] += boost
    return boosted


def semantic_search(
    query: str,
    *,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    products: Optional[Sequence[str]] = None,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    query_vector = _vectorize_query(cleaned_query)
    embedding_matrix, index_map = _load_embeddings()

    candidate_ids = (
        fetch_ids_for_segment(category, subcategory)
        if category and subcategory
        else fetch_all_ids()
    )
    if not candidate_ids:
        return []

    filtered_ids = [candidate_id for candidate_id in candidate_ids if candidate_id in index_map]
    if not filtered_ids:
        return []

    candidate_indices = np.array(
        [index_map[candidate_id] for candidate_id in filtered_ids],
        dtype=int,
    )
    candidate_vectors = embedding_matrix[candidate_indices]
    scores = candidate_vectors @ query_vector
    scores = _boost_by_products(scores, filtered_ids, products or [])

    top_indices = np.argsort(-scores)[:top_k]
    selected_ids = [filtered_ids[idx] for idx in top_indices]
    id_to_score = {filtered_ids[idx]: float(scores[idx]) for idx in top_indices}

    records = fetch_records_by_ids(selected_ids)
    results: List[Dict[str, Any]] = []
    for record_id in selected_ids:
        record = records.get(record_id)
        if not record:
            continue
        enriched = dict(record)
        enriched["score"] = id_to_score.get(record_id, 0.0)
        results.append(enriched)
    return results


def finalize(template: str, entities: Dict[str, str]) -> str:
    prepared_template = template.strip()
    if not prepared_template:
        return ""

    entity_pairs = "\n".join(f"{key}: {value}" for key, value in entities.items() if value)
    user_prompt = (
        "Шаблон ответа:\n"
        f"{prepared_template}\n\n"
        "Распознанные сущности:\n"
        f"{entity_pairs or 'нет данных'}\n\n"
        "Сформируй итоговый ответ."
    )

    client = get_scibox_client()
    response = client.chat(
        [
            {"role": "system", "content": FINALIZE_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )

    message = getattr(response, "content", "")
    if isinstance(message, str):
        return message.strip()

    parts: List[str] = []
    if isinstance(message, Iterable):
        for part in message:
            if getattr(part, "type", "") == "text":
                parts.append(getattr(part, "text", ""))
    return "".join(parts).strip()
