from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATS_DB_PATH = DATA_DIR / "stats.db"


@contextmanager
def _get_connection() -> Iterator[sqlite3.Connection]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(STATS_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def _ensure_column(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
    *,
    backfill_sql: str | None = None,
) -> bool:
    if _column_exists(conn, table, column):
        return False
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    if backfill_sql:
        conn.execute(backfill_sql)
    return True


def init_storage() -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                user_agent TEXT,
                latency_ms REAL,
                payload TEXT,
                extra TEXT
            )
            """
        )
        added_ts_column = _ensure_column(
            conn,
            "events",
            "ts",
            "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            backfill_sql="UPDATE events SET ts = CURRENT_TIMESTAMP WHERE ts IS NULL",
        )
        if added_ts_column:
            conn.commit()
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_kind_ts
            ON events(kind, ts DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS classification_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                category TEXT,
                subcategory TEXT,
                target TEXT NOT NULL CHECK(target IN ('main', 'sub')),
                is_correct INTEGER NOT NULL CHECK(is_correct IN (0, 1))
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_classification_votes_pair
            ON classification_votes(category, subcategory, target)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS template_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                is_positive INTEGER NOT NULL CHECK(is_positive IN (0, 1))
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_template_votes_ts
            ON template_votes(ts DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS request_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                query TEXT NOT NULL,
                category TEXT,
                subcategory TEXT,
                main_vote INTEGER,
                sub_vote INTEGER,
                template_text TEXT,
                template_positive INTEGER,
                top_item_id INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_request_history_ts
            ON request_history(ts DESC)
            """
        )
        conn.commit()


def log_event(
    kind: str,
    *,
    session_id: Optional[str] = None,
    user_agent: Optional[str] = None,
    latency_ms: Optional[float] = None,
    payload: Optional[Dict[str, object]] = None,
    extra: Optional[Dict[str, object]] = None,
) -> None:
    record = (
        kind.strip(),
        session_id.strip() if session_id else None,
        user_agent.strip() if user_agent else None,
        float(latency_ms) if latency_ms is not None else None,
        json.dumps(payload or {}, ensure_ascii=False),
        json.dumps(extra or {}, ensure_ascii=False),
    )
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO events (kind, session_id, user_agent, latency_ms, payload, extra)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            record,
        )
        conn.commit()


@dataclass
class AggregateResult:
    total: int = 0
    success: int = 0
    total_latency: float = 0.0
    total_score: float = 0.0
    score_samples: int = 0


def _fetch_scalar(query: str, params: Iterable[object] = ()) -> float:
    with _get_connection() as conn:
        row = conn.execute(query, tuple(params)).fetchone()
        if not row:
            return 0.0
        value = row[0]
    return float(value or 0.0)


def _fetch_recent(limit: int = 10) -> List[Dict[str, object]]:
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, kind, ts as timestamp, session_id, payload
            FROM events
            ORDER BY ts DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    results: List[Dict[str, object]] = []
    for row in rows:
        payload: Dict[str, object] = {}
        try:
            payload = json.loads(row["payload"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        detail = ""
        if row["kind"] == "search":
            detail = f"results={payload.get('result_count', 0)}"
        elif row["kind"] == "classify":
            detail = f"confidence={payload.get('confidence', 0):.2f}"
        elif row["kind"] == "feedback":
            detail = "useful" if payload.get("useful") else "not useful"
        results.append(
            {
                "id": int(row["id"]),
                "kind": row["kind"],
                "timestamp": datetime.fromisoformat(row["timestamp"])
                if isinstance(row["timestamp"], str)
                else row["timestamp"],
                "session_id": row["session_id"],
                "detail": detail,
            }
        )
    return results


def _build_bucket(
    *,
    total: float,
    success: float,
    avg_latency: float,
    avg_score: float,
) -> Dict[str, object]:
    total_int = int(total)
    success_int = int(success)
    rate = success_int / total_int if total_int else 0.0
    return {
        "total": total_int,
        "success": success_int,
        "success_rate": rate,
        "avg_latency_ms": avg_latency if total_int else None,
        "avg_score": avg_score if total_int else None,
    }


def _build_feedback_stats(
    *,
    total: float,
    positive: float,
) -> Dict[str, object]:
    total_int = int(total)
    positive_int = int(positive)
    negative_int = max(total_int - positive_int, 0)
    rate = positive_int / total_int if total_int else 0.0
    return {
        "total": total_int,
        "positive": positive_int,
        "negative": negative_int,
        "positive_rate": rate,
    }


def record_classification_vote(
    *,
    category: Optional[str],
    subcategory: Optional[str],
    target: str,
    is_correct: bool,
    session_id: Optional[str],
) -> None:
    normalized_category = category.strip() if category else None
    normalized_subcategory = subcategory.strip() if subcategory else None
    normalized_session = session_id.strip() if session_id else None
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO classification_votes (session_id, category, subcategory, target, is_correct)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                normalized_session,
                normalized_category,
                normalized_subcategory,
                target,
                1 if is_correct else 0,
            ),
        )
        conn.commit()


def record_template_vote(*, is_positive: bool, session_id: Optional[str]) -> None:
    normalized_session = session_id.strip() if session_id else None
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO template_votes (session_id, is_positive)
            VALUES (?, ?)
            """,
            (normalized_session, 1 if is_positive else 0),
        )
        conn.commit()


def record_request_history(
    *,
    query: str,
    session_id: Optional[str],
    category: Optional[str],
    subcategory: Optional[str],
    main_vote: Optional[bool],
    sub_vote: Optional[bool],
    template_text: Optional[str],
    template_positive: Optional[bool],
    top_item_id: Optional[int],
) -> None:
    normalized_session = session_id.strip() if session_id else None
    normalized_category = category.strip() if category else None
    normalized_subcategory = subcategory.strip() if subcategory else None
    normalized_query = query.strip()
    normalized_template = template_text.strip() if template_text else None
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO request_history (
                session_id,
                query,
                category,
                subcategory,
                main_vote,
                sub_vote,
                template_text,
                template_positive,
                top_item_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_session,
                normalized_query,
                normalized_category,
                normalized_subcategory,
                None if main_vote is None else int(bool(main_vote)),
                None if sub_vote is None else int(bool(sub_vote)),
                normalized_template,
                None if template_positive is None else int(bool(template_positive)),
                top_item_id,
            ),
        )
        conn.commit()


def _build_vote_breakdown(total: float, correct: float) -> Dict[str, object]:
    total_int = int(total)
    correct_int = int(correct)
    accuracy = correct_int / total_int if total_int else 0.0
    return {
        "total": total_int,
        "correct": correct_int,
        "accuracy": accuracy,
    }


def fetch_classification_quality(limit_pairs: int = 10) -> Dict[str, object]:
    with _get_connection() as conn:
        totals = conn.execute(
            """
            SELECT target, SUM(is_correct) AS correct, COUNT(*) AS total
            FROM classification_votes
            GROUP BY target
            """
        ).fetchall()

        pairs = conn.execute(
            """
            SELECT
                category,
                subcategory,
                SUM(CASE WHEN target = 'main' THEN 1 ELSE 0 END) AS main_total,
                SUM(CASE WHEN target = 'main' AND is_correct = 1 THEN 1 ELSE 0 END) AS main_correct,
                SUM(CASE WHEN target = 'sub' THEN 1 ELSE 0 END) AS sub_total,
                SUM(CASE WHEN target = 'sub' AND is_correct = 1 THEN 1 ELSE 0 END) AS sub_correct
            FROM classification_votes
            GROUP BY category, subcategory
            ORDER BY (main_total + sub_total) DESC, category, subcategory
            LIMIT ?
            """,
            (limit_pairs,),
        ).fetchall()

    overall_main: Tuple[float, float] = (0.0, 0.0)
    overall_sub: Tuple[float, float] = (0.0, 0.0)
    for row in totals:
        target = row["target"]
        correct = float(row["correct"] or 0.0)
        total = float(row["total"] or 0.0)
        if target == "main":
            overall_main = (total, correct)
        elif target == "sub":
            overall_sub = (total, correct)

    pair_list: List[Dict[str, object]] = []
    for row in pairs:
        main_total = float(row["main_total"] or 0.0)
        main_correct = float(row["main_correct"] or 0.0)
        sub_total = float(row["sub_total"] or 0.0)
        sub_correct = float(row["sub_correct"] or 0.0)
        pair_list.append(
            {
                "category": row["category"],
                "subcategory": row["subcategory"],
                "main": _build_vote_breakdown(main_total, main_correct),
                "sub": _build_vote_breakdown(sub_total, sub_correct),
            }
        )

    return {
        "overall_main": _build_vote_breakdown(*overall_main),
        "overall_sub": _build_vote_breakdown(*overall_sub),
        "pairs": pair_list,
    }


def fetch_template_quality() -> Dict[str, object]:
    with _get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                SUM(is_positive) AS positive,
                COUNT(*) AS total
            FROM template_votes
            """
        ).fetchone()
    total = float(row["total"] or 0.0) if row else 0.0
    positive = float(row["positive"] or 0.0) if row else 0.0
    return _build_feedback_stats(total=total, positive=positive)


def fetch_request_history(limit: int = 20) -> List[Dict[str, object]]:
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                ts AS timestamp,
                session_id,
                query,
                category,
                subcategory,
                main_vote,
                sub_vote,
                template_text,
                template_positive,
                top_item_id
            FROM request_history
            ORDER BY ts DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    history: List[Dict[str, object]] = []
    for row in rows:
        timestamp_raw = row["timestamp"]
        if isinstance(timestamp_raw, str):
            timestamp = datetime.fromisoformat(timestamp_raw)
        else:
            timestamp = timestamp_raw
        history.append(
            {
                "id": int(row["id"]),
                "timestamp": timestamp,
                "session_id": row["session_id"],
                "query": row["query"],
                "category": row["category"],
                "subcategory": row["subcategory"],
                "main_vote": None
                if row["main_vote"] is None
                else bool(row["main_vote"]),
                "sub_vote": None
                if row["sub_vote"] is None
                else bool(row["sub_vote"]),
                "template_text": row["template_text"],
                "template_positive": None
                if row["template_positive"] is None
                else bool(row["template_positive"]),
                "top_item_id": row["top_item_id"],
            }
        )
    return history


def fetch_summary(
    limit_recent: int = 10,
    *,
    pair_limit: int = 8,
    history_limit: int = 15,
) -> Dict[str, object]:
    search_total = _fetch_scalar(
        "SELECT COUNT(*) FROM events WHERE kind = 'search'"
    )
    search_success = _fetch_scalar(
        """
        SELECT COUNT(*)
        FROM events
        WHERE kind = 'search'
          AND json_extract(payload, '$.result_count') > 0
        """
    )
    search_latency = _fetch_scalar(
        "SELECT AVG(latency_ms) FROM events WHERE kind = 'search'"
    )
    search_score = _fetch_scalar(
        """
        SELECT AVG(json_extract(payload, '$.top_score'))
        FROM events
        WHERE kind = 'search'
          AND json_extract(payload, '$.top_score') IS NOT NULL
        """
    )

    classify_total = _fetch_scalar(
        "SELECT COUNT(*) FROM events WHERE kind = 'classify'"
    )
    classify_success = _fetch_scalar(
        """
        SELECT COUNT(*)
        FROM events
        WHERE kind = 'classify'
          AND json_extract(payload, '$.confidence') >= 0.5
        """
    )
    classify_latency = _fetch_scalar(
        "SELECT AVG(latency_ms) FROM events WHERE kind = 'classify'"
    )
    classify_score = _fetch_scalar(
        """
        SELECT AVG(json_extract(payload, '$.confidence'))
        FROM events
        WHERE kind = 'classify'
          AND json_extract(payload, '$.confidence') IS NOT NULL
        """
    )

    feedback_total = _fetch_scalar(
        "SELECT COUNT(*) FROM events WHERE kind = 'feedback'"
    )
    feedback_positive = _fetch_scalar(
        """
        SELECT COUNT(*)
        FROM events
        WHERE kind = 'feedback'
          AND json_extract(payload, '$.useful') = 1
        """
    )

    recent_events = _fetch_recent(limit_recent)

    quality = {
        "classification": fetch_classification_quality(limit_pairs=pair_limit),
        "templates": fetch_template_quality(),
    }

    history = fetch_request_history(limit=history_limit)

    return {
        "search": _build_bucket(
            total=search_total,
            success=search_success,
            avg_latency=search_latency,
            avg_score=search_score,
        ),
        "classify": _build_bucket(
            total=classify_total,
            success=classify_success,
            avg_latency=classify_latency,
            avg_score=classify_score,
        ),
        "feedback": _build_feedback_stats(
            total=feedback_total,
            positive=feedback_positive,
        ),
        "recent": recent_events,
        "quality": quality,
        "history": history,
    }
