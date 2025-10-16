from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "faq.db"


def _get_connection() -> sqlite3.Connection:
    """Создать новое соединение с базой FAQ."""
    if not DB_PATH.exists():
        raise FileNotFoundError("База знаний FAQ не найдена. Запустите build_index.py.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@lru_cache
def fetch_categories() -> List[str]:
    """Получить список всех основных категорий."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM faq ORDER BY category COLLATE NOCASE"
        ).fetchall()
    return [row["category"] for row in rows]


@lru_cache
def fetch_subcategories(category: str) -> List[str]:
    """Получить список подкатегорий для выбранной основной категории."""
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT subcategory
            FROM faq
            WHERE category = ?
            ORDER BY subcategory COLLATE NOCASE
            """,
            (category,),
        ).fetchall()
    return [row["subcategory"] for row in rows]


def fetch_ids_for_segment(category: str, subcategory: str) -> List[int]:
    """Вернуть идентификаторы записей для указанного сегмента."""
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id
            FROM faq
            WHERE category = ? AND subcategory = ?
            ORDER BY id
            """,
            (category, subcategory),
        ).fetchall()
    return [int(row["id"]) for row in rows]


@lru_cache
def fetch_all_ids() -> List[int]:
    """Вернуть идентификаторы всех записей FAQ в порядке возрастания."""
    with _get_connection() as conn:
        rows = conn.execute("SELECT id FROM faq ORDER BY id").fetchall()
    return [int(row["id"]) for row in rows]


def fetch_records_by_ids(ids: Iterable[int]) -> Dict[int, Dict[str, str]]:
    """Получить набор записей FAQ по списку идентификаторов."""
    ids = list(ids)
    if not ids:
        return {}

    placeholders = ",".join("?" for _ in ids)
    query = (
        f"SELECT id, category, subcategory, audience, question, answer "
        f"FROM faq WHERE id IN ({placeholders})"
    )

    with _get_connection() as conn:
        rows = conn.execute(query, ids).fetchall()

    return {
        int(row["id"]): {
            "id": int(row["id"]),
            "category": row["category"],
            "subcategory": row["subcategory"],
            "audience": row["audience"],
            "question": row["question"],
            "answer": row["answer"],
        }
        for row in rows
    }


def fetch_records_for_category(category: str) -> List[Dict[str, str]]:
    """Вернуть все записи FAQ для заданной категории."""
    if not category:
        return []

    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, subcategory, question, answer
            FROM faq
            WHERE category = ?
            """,
            (category,),
        ).fetchall()

    return [
        {
            "id": int(row["id"]),
            "subcategory": row["subcategory"],
            "question": row["question"],
            "answer": row["answer"],
        }
        for row in rows
    ]


def fetch_all_templates() -> List[Dict[str, str]]:
    """Получить все шаблонные вопросы со связанной категорией и подкатегорией."""
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                question,
                answer,
                category,
                subcategory
            FROM faq
            ORDER BY id
            """
        ).fetchall()

    return [
        {
            "id": int(row["id"]),
            "question": row["question"],
            "answer": row["answer"],
            "category": row["category"],
            "subcategory": row["subcategory"],
        }
        for row in rows
    ]


def fetch_template_embeddings(ids: Iterable[int]) -> Dict[int, np.ndarray]:
    
    id_list = sorted({int(value) for value in ids})
    if not id_list:
        return {}

    placeholders = ",".join("?" for _ in id_list)
    query = (
        f"SELECT faq_id, vector, dimension FROM faq_embeddings "
        f"WHERE faq_id IN ({placeholders})"
    )

    with _get_connection() as conn:
        rows = conn.execute(query, id_list).fetchall()

    if not rows:
        raise RuntimeError("FAQ embeddings are missing. Please rebuild the index.")

    result: Dict[int, np.ndarray] = {}
    for row in rows:
        faq_id = int(row["faq_id"])
        vector = np.frombuffer(row["vector"], dtype=np.float32)
        dimension = int(row["dimension"])
        if vector.size != dimension:
            raise RuntimeError(f"Embedding dimension mismatch for faq_id={faq_id}.")
        result[faq_id] = vector.copy()
    return result


def fetch_all_embeddings() -> Tuple[List[int], np.ndarray]:
   
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT faq_id, vector, dimension FROM faq_embeddings ORDER BY faq_id"
        ).fetchall()

    if not rows:
        raise RuntimeError("FAQ embeddings are missing. Please rebuild the index.")

    ids: List[int] = []
    vectors: List[np.ndarray] = []
    for row in rows:
        faq_id = int(row["faq_id"])
        vector = np.frombuffer(row["vector"], dtype=np.float32)
        dimension = int(row["dimension"])
        if vector.size != dimension:
            raise RuntimeError(f"Embedding dimension mismatch for faq_id={faq_id}.")
        ids.append(faq_id)
        vectors.append(vector.copy())

    matrix = np.vstack(vectors).astype(np.float32)
    return ids, matrix
