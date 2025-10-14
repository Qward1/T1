from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATS_DB_PATH = DATA_DIR / "stats.db"


def _get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(STATS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_stats_db() -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS classification_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                subcategory TEXT,
                is_correct INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS template_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                is_positive INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS request_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                category TEXT,
                subcategory TEXT,
                template_id INTEGER,
                final_answer TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def record_classification_feedback(category: str, subcategory: str, is_correct: bool) -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO classification_feedback (category, subcategory, is_correct)
            VALUES (?, ?, ?)
            """,
            (category.strip(), subcategory.strip(), int(bool(is_correct))),
        )
        conn.commit()


def record_template_feedback(is_positive: bool) -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO template_feedback (is_positive)
            VALUES (?)
            """,
            (int(bool(is_positive)),),
        )
        conn.commit()


def record_request_history(
    query: str,
    category: str | None,
    subcategory: str | None,
    template_id: int | None,
    final_answer: str,
) -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO request_history (query, category, subcategory, template_id, final_answer)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                query,
                (category or "").strip(),
                (subcategory or "").strip(),
                template_id,
                final_answer,
            ),
        )
        conn.commit()


def get_classification_stats() -> List[Dict[str, object]]:
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                COALESCE(NULLIF(category, ''), '—') AS category,
                COALESCE(NULLIF(subcategory, ''), '—') AS subcategory,
                SUM(is_correct) AS correct,
                COUNT(*) AS total
            FROM classification_feedback
            GROUP BY category, subcategory
            ORDER BY total DESC, category, subcategory
            """
        ).fetchall()
    stats: List[Dict[str, object]] = []
    for row in rows:
        total = row["total"] or 0
        correct = row["correct"] or 0
        incorrect = max(total - correct, 0)
        accuracy = correct / total if total else 0.0
        stats.append(
            {
                "category": row["category"],
                "subcategory": row["subcategory"],
                "correct": int(correct),
                "incorrect": int(incorrect),
                "accuracy": accuracy,
            }
        )
    return stats


def get_template_stats() -> Dict[str, object]:
    with _get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                SUM(is_positive) AS positive,
                COUNT(*) - SUM(is_positive) AS negative,
                COUNT(*) AS total
            FROM template_feedback
            """
        ).fetchone()
    positive = (row["positive"] or 0) if row else 0
    negative = (row["negative"] or 0) if row else 0
    total = (row["total"] or 0) if row else 0
    accuracy = positive / total if total else 0.0
    return {
        "positive": int(positive),
        "negative": int(negative),
        "accuracy": accuracy,
    }


def get_recent_history(limit: int = 20) -> List[Dict[str, object]]:
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                query,
                category,
                subcategory,
                template_id,
                final_answer,
                created_at
            FROM request_history
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    history: List[Dict[str, object]] = []
    for row in rows:
        history.append(
            {
                "id": int(row["id"]),
                "query": row["query"],
                "category": row["category"] or "",
                "subcategory": row["subcategory"] or "",
                "template_id": row["template_id"],
                "final_answer": row["final_answer"] or "",
                "created_at": row["created_at"],
            }
        )
    return history

