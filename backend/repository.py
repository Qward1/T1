from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List

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

