from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, List

import numpy as np
import pandas as pd

from .scibox_client import get_scibox_client
from .settings import get_settings

BATCH_SIZE = 64
COLUMN_MAP = {
    "Основная категория": "category",
    "Подкатегория": "subcategory",
    "Целевая аудитория": "audience",
    "Пример вопроса": "question",
    "Шаблонный ответ": "answer",
}
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "faq.db"
EMBEDDINGS_PATH = DATA_DIR / "faq_embeddings.npy"


def _prepare_dataframe(source_path: Path) -> pd.DataFrame:
    """Загрузить таблицу FAQ, переименовать колонки и удалить пустые строки."""
    df = pd.read_excel(source_path)
    if missing := set(COLUMN_MAP).difference(df.columns):
        raise ValueError(f"В таблице FAQ отсутствуют колонки: {', '.join(sorted(missing))}")

    df = df.rename(columns=COLUMN_MAP)
    df = df[list(COLUMN_MAP.values())]
    df = df.dropna(subset=["question", "answer"])
    df = df.fillna("")  # Заменяем оставшиеся NaN на пустые строки
    return df


def _batched(iterable: Iterable[str], size: int) -> Iterable[List[str]]:
    """Разбить последовательность на батчи фиксированного размера."""
    batch: List[str] = []
    for item in iterable:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def _reset_database(df: pd.DataFrame) -> None:
    """Пересобрать SQLite-базу с данными FAQ."""
    if DB_PATH.exists():
        try:
            DB_PATH.unlink()
        except PermissionError as exc:
            raise RuntimeError(
                "Не удалось перезаписать базу FAQ (faq.db). Закройте процессы, которые используют файл, "
                "например запущенный backend или открытый просмотрщик БД, и повторите попытку."
            ) from exc

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
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
        records = [
            (
                int(row.id),
                row.category,
                row.subcategory,
                row.audience,
                row.question,
                row.answer,
            )
            for row in df.itertuples(index=False)
        ]
        conn.executemany(
            """
            INSERT INTO faq (id, category, subcategory, audience, question, answer)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            records,
        )
        conn.execute("CREATE INDEX idx_faq_category ON faq(category)")
        conn.execute("CREATE INDEX idx_faq_category_subcategory ON faq(category, subcategory)")
        conn.commit()
    finally:
        conn.close()


def _save_embeddings(embeddings: List[List[float]]) -> None:
    """Сохранить нормализованные эмбеддинги в виде NumPy-массива."""
    if not embeddings:
        raise RuntimeError("Не удалось сгенерировать эмбеддинги для FAQ.")

    vectors = np.array(embeddings, dtype="float32")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    vectors = vectors / norms

    if EMBEDDINGS_PATH.exists():
        EMBEDDINGS_PATH.unlink()

    np.save(EMBEDDINGS_PATH, vectors)


def build_faq_index() -> None:
    """Импортировать FAQ из Excel в SQLite и подготовить эмбеддинги вопросов."""
    settings = get_settings()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    df = _prepare_dataframe(settings.faq_source_path)
    df = df.reset_index(drop=True)
    df.insert(0, "id", df.index + 1)

    _reset_database(df)

    client = get_scibox_client()
    embeddings: List[List[float]] = []
    for batch in _batched(df["question"], BATCH_SIZE):
        embeddings.extend(client.embed(batch))

    _save_embeddings(embeddings)


if __name__ == "__main__":
    build_faq_index()
