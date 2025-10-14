from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .repository import fetch_all_ids, fetch_ids_for_segment, fetch_records_by_ids
from .scibox_client import get_scibox_client

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EMBEDDINGS_PATH = DATA_DIR / "faq_embeddings.npy"

FINALIZE_PROMPT = (
    "Ты помощник оператора поддержки. "
    "У тебя есть шаблон ответа. "
    "Используй только информацию из шаблона, чтобы подготовить финальный текст для клиента. "
    "Если в шаблоне встречаются плейсхолдеры в фигурных скобках, аккуратно подставь значения из entities. "
    "Не добавляй новых фактов и не упоминай, что шаблон был использован."
)


@lru_cache
def _load_embeddings() -> np.ndarray:
    """Загрузить матрицу нормализованных эмбеддингов вопросов FAQ."""
    if not EMBEDDINGS_PATH.exists():
        raise FileNotFoundError("Файл с эмбеддингами не найден. Запустите build_index.py.")
    return np.load(EMBEDDINGS_PATH)


def _vectorize_query(text: str) -> np.ndarray:
    """Преобразовать пользовательский запрос в нормализованный вектор."""
    client = get_scibox_client()
    [embedding] = client.embed([text])
    vector = np.array(embedding, dtype="float32")
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return vector / norm


def semantic_search(
    query: str,
    *,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    products: Optional[Sequence[str]] = None,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """Выполнить семантический поиск с возможным учётом сегмента и упомянутых продуктов."""
    query = query.strip()
    if not query:
        return []

    query_vector = _vectorize_query(query)
    embeddings = _load_embeddings()

    if category and subcategory:
        candidate_ids = fetch_ids_for_segment(category, subcategory)
    else:
        candidate_ids = fetch_all_ids()

    if not candidate_ids:
        return []

    indices = np.array([idx - 1 for idx in candidate_ids], dtype=int)
    candidate_vectors = embeddings[indices]
    scores = candidate_vectors @ query_vector

    products_lower = [p.casefold() for p in (products or []) if p]
    if products_lower:
        scores = scores.copy()
        records_map = fetch_records_by_ids(candidate_ids)
        for idx, record_id in enumerate(candidate_ids):
            record = records_map.get(record_id)
            if not record:
                continue
            text = f"{record.get('question', '')} {record.get('answer', '')}".casefold()
            boost = 0.0
            for product in products_lower:
                if product and product in text:
                    boost += 0.1
            scores[idx] += boost

    top_indices = np.argsort(-scores)[:top_k]
    selected_ids = [candidate_ids[idx] for idx in top_indices]
    id_to_score = {candidate_ids[idx]: float(scores[idx]) for idx in top_indices}

    records = fetch_records_by_ids(selected_ids)

    results: List[Dict[str, Any]] = []
    for record_id in selected_ids:
        record = records.get(record_id)
        if not record:
            continue
        entry = dict(record)
        entry["score"] = id_to_score.get(record_id, 0.0)
        results.append(entry)
    return results


def finalize(template: str, entities: Dict[str, str]) -> str:
    """Сформировать финальный ответ на основе шаблона и найденных сущностей."""
    template = template.strip()
    if not template:
        return ""

    entity_pairs = "\n".join(f"{key}: {value}" for key, value in entities.items() if value)
    user_prompt = (
        "Шаблон ответа:\n"
        f"{template}\n\n"
        "Известные сущности:\n"
        f"{entity_pairs or 'нет данных'}\n\n"
        "Подготовь финальный ответ."
    )

    client = get_scibox_client()
    response = client.chat(
        [
            {"role": "system", "content": FINALIZE_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )
    return _extract_content(response).strip()


def _extract_content(message: Any) -> str:
    """Аккуратно извлечь текст из ответа чат-модели."""
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            getattr(part, "text", "")
            for part in content
            if getattr(part, "type", "") == "text"
        ]
        return "".join(parts)
    return ""

