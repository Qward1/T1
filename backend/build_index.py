from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Iterator, List

import numpy as np
import pandas as pd

from .scibox_client import get_scibox_client
from .settings import get_settings

BATCH_SIZE = 64
COLUMN_MAP = {
    "Категория обращения": "category",
    "Подкатегория": "subcategory",
    "Аудитория": "audience",
    "Вопрос клиента": "question",
    "Шаблон ответа": "answer",
}
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "faq.db"
EMBEDDINGS_PATH = DATA_DIR / "faq_embeddings.npy"


def _prepare_dataframe(source_path: Path) -> pd.DataFrame:
    dataframe = pd.read_excel(source_path)
    missing = set(COLUMN_MAP).difference(dataframe.columns)
    if missing:
        raise ValueError(f"В файле FAQ отсутствуют столбцы: {', '.join(sorted(missing))}")

    dataframe = dataframe.rename(columns=COLUMN_MAP)
    dataframe = dataframe[list(COLUMN_MAP.values())]
    dataframe = dataframe.dropna(subset=["question", "answer"])
    dataframe = dataframe.fillna("")
    return dataframe


def _batched(items: Iterable[str], size: int) -> Iterator[List[str]]:
    chunk: List[str] = []
    for item in items:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _reset_database(dataframe: pd.DataFrame) -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute(
            """
            CREATE TABLE faq (
                id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                subcategory TEXT NOT NULL,
                audience TEXT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL
            )
            """
        )
        rows = [
            (
                int(row.id),
                row.category,
                row.subcategory,
                row.audience,
                row.question,
                row.answer,
            )
            for row in dataframe.itertuples(index=False)
        ]
        connection.executemany(
            """
            INSERT INTO faq (id, category, subcategory, audience, question, answer)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.execute("CREATE INDEX idx_faq_category ON faq(category)")
        connection.execute(
            "CREATE INDEX idx_faq_category_subcategory ON faq(category, subcategory)"
        )
        connection.commit()
    finally:
        connection.close()


def _save_embeddings(embeddings: List[List[float]]) -> None:
    if not embeddings:
        raise RuntimeError("Не удалось получить эмбеддинги для FAQ.")

    vectors = np.array(embeddings, dtype="float32")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    vectors = vectors / norms

    if EMBEDDINGS_PATH.exists():
        EMBEDDINGS_PATH.unlink()
    np.save(EMBEDDINGS_PATH, vectors)


def build_faq_index() -> int:
    """Rebuild SQLite index and embedding matrix. Returns number of stored records."""
    settings = get_settings()
    source_path = settings.faq_source_path
    if not source_path:
        raise RuntimeError("FAQ_PATH is not configured.")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    dataframe = _prepare_dataframe(source_path)
    dataframe = dataframe.reset_index(drop=True)
    dataframe.insert(0, "id", dataframe.index + 1)

    _reset_database(dataframe)

    client = get_scibox_client()
    embeddings: List[List[float]] = []
    for batch in _batched(dataframe["question"], BATCH_SIZE):
        embeddings.extend(client.embed(batch))

    _save_embeddings(embeddings)
    return len(dataframe)


if __name__ == "__main__":
    build_faq_index()
