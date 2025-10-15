import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SCIBOX_API_KEY", "test-key")
os.environ.setdefault("SCIBOX_BASE_URL", "http://dummy.local")


@pytest.fixture
def client(monkeypatch):
    from backend import settings
    from backend.api import app

    settings.get_settings.cache_clear()

    monkeypatch.setattr("backend.services.logic.perform_warmup", lambda: None)

    sample_result = [
        {
            "id": 1,
            "question": "Как оплатить счёт?",
            "answer": "Используйте личный кабинет для оплаты счёта.",
            "title": "Как оплатить счёт?",
            "category": "Биллинг",
            "subcategory": "Счета",
            "score": 0.98,
        }
    ]

    monkeypatch.setattr(
        "backend.services.logic.semantic_search",
        lambda query, top_k=5: sample_result,
    )

    def fake_classify_and_ner(text):
        return {
            "category": "Биллинг",
            "subcategory": "Счета",
            "category_confidence": 0.91,
            "subcategory_confidence": 0.87,
            "confidence": 0.87,
            "entities": {"problem": "оплата"},
        }

    monkeypatch.setattr(
        "backend.services.logic.classify_and_ner",
        fake_classify_and_ner,
    )

    with TestClient(app) as test_client:
        yield test_client


def test_search_endpoint(client):
    response = client.post(
        "/api/search",
        json={"query": "как оплатить", "top_k": 3, "session_id": "session-1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    assert payload["results"][0]["title"] == "Как оплатить счёт?"


def test_classify_endpoint(client):
    response = client.post(
        "/api/classify",
        json={"text": "Мне нужен счёт", "session_id": "session-2"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["label"]
    assert payload["raw"]["category"] == "Биллинг"


def test_feedback_and_stats(client):
    feedback_response = client.post(
        "/api/feedback",
        json={
            "query": "как оплатить",
            "item_id": 1,
            "useful": True,
            "session_id": "session-3",
        },
    )
    assert feedback_response.status_code == 200
    assert feedback_response.json()["ok"] is True

    stats_response = client.get("/api/stats/summary")
    assert stats_response.status_code == 200
    summary = stats_response.json()
    assert "search" in summary
    assert "classify" in summary
    assert "feedback" in summary
