from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Sequence

import faiss  # type: ignore
import numpy as np

from .scibox_client import get_scibox_client

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INDEX_PATH = DATA_DIR / "faq.index"
RECORDS_PATH = DATA_DIR / "faq_records.json"

FINALIZE_PROMPT = (
    "Ты помощник оператора поддержки. "
    "У тебя есть шаблон ответа. "
    "Используй только информацию из шаблона, чтобы сформировать финальный ответ. "
    "Если в шаблоне присутствуют фигурные скобки или плейсхолдеры, аккуратно подставь значения из entities. "
    "Не добавляй новых фактов и не упоминай, что шаблон был использован."
)


@lru_cache
def _load_index() -> faiss.Index:
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"FAISS index not found at {INDEX_PATH}. Run build_index.py first.")
    return faiss.read_index(str(INDEX_PATH))


@lru_cache
def _load_records() -> List[Dict[str, str]]:
    if not RECORDS_PATH.exists():
        raise FileNotFoundError(f"FAQ records not found at {RECORDS_PATH}. Run build_index.py first.")
    return json.loads(RECORDS_PATH.read_text(encoding="utf-8"))


def retrieve(text: str, top_k: int = 10) -> List[Dict[str, str]]:
    """Return top-k FAQ templates most relevant to the query."""
    if not text or not text.strip():
        return []

    client = get_scibox_client()
    [embedding] = client.embed([text])

    query = np.array([embedding], dtype="float32")
    faiss.normalize_L2(query)

    index = _load_index()
    records = _load_records()

    k = min(top_k, len(records))
    scores, indices = index.search(query, k)

    results: List[Dict[str, str]] = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        record = records[idx].copy()
        record["score"] = float(score)
        results.append(record)
    return results


def rerank(
    candidates: Sequence[Dict[str, str]],
    meta: Dict[str, str] | None = None,
) -> List[Dict[str, str]]:
    """Apply simple rule-based boosts using classification metadata."""
    meta = meta or {}
    category = (meta.get("category") or "").lower()
    subcategory = (meta.get("subcategory") or "").lower()

    def _score(candidate: Dict[str, str]) -> float:
        score = float(candidate.get("score", 0.0))
        if candidate.get("category", "").lower() == category:
            score += 0.1
        if candidate.get("subcategory", "").lower() == subcategory:
            score += 0.1
        return score

    return sorted(candidates, key=_score, reverse=True)


def finalize(template: str, entities: Dict[str, str]) -> str:
    """Generate the final response by adapting the template with entities."""
    template = template.strip()
    if not template:
        return ""

    entity_pairs = "\n".join(f"{key}: {value}" for key, value in entities.items() if value)
    user_prompt = (
        "Шаблон ответа:\n"
        f"{template}\n\n"
        "Известные сущности:\n"
        f"{entity_pairs or 'нет данных'}\n\n"
        "Сформируй финальный ответ."
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
