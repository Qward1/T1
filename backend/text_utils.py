from __future__ import annotations

from typing import Tuple

from simplemma import lemmatize, simple_tokenizer

LEMMA_LANGS: Tuple[str, ...] = ("ru", "en")


def normalize_text(value: str) -> str:
    """Return a space-delimited string of lemmas for downstream embedding."""
    if not value:
        return ""
    tokens = [token for token in simple_tokenizer(value.lower()) if token.strip()]
    if not tokens:
        return ""
    lemmas = [lemmatize(token, LEMMA_LANGS) or token for token in tokens]
    return " ".join(lemmas)

