from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

import faiss  # type: ignore
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
INDEX_PATH = DATA_DIR / "faq.index"
RECORDS_PATH = DATA_DIR / "faq_records.json"


def _prepare_dataframe(source_path: Path) -> pd.DataFrame:
    """Load FAQ data, rename columns, and drop incomplete rows."""
    df = pd.read_excel(source_path)
    if missing := set(COLUMN_MAP).difference(df.columns):
        raise ValueError(f"FAQ source missing columns: {', '.join(sorted(missing))}")

    df = df.rename(columns=COLUMN_MAP)
    df = df[list(COLUMN_MAP.values())]
    df = df.dropna(subset=["question", "answer"])
    df = df.fillna("")  # replace remaining NaNs with empty strings
    return df


def _batched(iterable: Iterable[str], size: int) -> Iterable[List[str]]:
    """Yield fixed-size batches from an iterable."""
    batch: List[str] = []
    for item in iterable:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def build_faq_index() -> None:
    """Build FAQ records and FAISS index from the Excel source."""
    settings = get_settings()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if INDEX_PATH.exists() and RECORDS_PATH.exists():
        return

    df = _prepare_dataframe(settings.faq_source_path)
    client = get_scibox_client()

    embeddings: List[List[float]] = []
    for batch in _batched(df["question"], BATCH_SIZE):
        embeddings.extend(client.embed(batch))

    if not embeddings:
        raise RuntimeError("No embeddings were generated for the FAQ dataset.")

    vectors = np.array(embeddings, dtype="float32")
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    records = [
        {
            "id": idx,
            "category": row["category"],
            "subcategory": row["subcategory"],
            "audience": row["audience"],
            "question": row["question"],
            "answer": row["answer"],
        }
        for idx, row in df.reset_index(drop=True).iterrows()
    ]

    faiss.write_index(index, str(INDEX_PATH))
    RECORDS_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    build_faq_index()
