from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .classifiers import classify_and_ner
from .recommenders import DATA_DIR, finalize, semantic_search
from openai import RateLimitError

app = FastAPI(title="Smart Support Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1)


class Recommendation(BaseModel):
    id: int
    category: str
    subcategory: str
    audience: str | None = None
    question: str
    answer: str
    score: float


class AnalyzeResponse(BaseModel):
    category: str
    category_confidence: float
    subcategory: str
    subcategory_confidence: float
    confidence: float
    entities: Dict[str, str]
    products: List[str]
    recommendations: List[Recommendation]


class RespondRequest(BaseModel):
    template: str = Field(..., min_length=1)
    entities: Dict[str, str]


class RespondResponse(BaseModel):
    answer: str


class FeedbackRequest(BaseModel):
    query: str
    category: str | None = None
    subcategory: str | None = None
    selected_template_id: int | None = None
    final_answer: str
    is_helpful: bool
    notes: str | None = None


class FeedbackResponse(BaseModel):
    status: str


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        classification = classify_and_ner(request.text)
    except RateLimitError as exc:
        raise HTTPException(
            status_code=503,
            detail="Модель временно недоступна из-за ограничения на количество запросов. Повторите попытку чуть позже.",
        ) from exc

    use_segment = (
        classification["category"]
        and classification["subcategory"]
        and classification["category_confidence"] >= 0.5
        and classification["subcategory_confidence"] >= 0.5
    )

    recommendations = semantic_search(
        request.text,
        category=classification["category"] if use_segment else None,
        subcategory=classification["subcategory"] if use_segment else None,
        products=classification.get("products") or [],
        top_k=3,
    )

    if use_segment and not recommendations:
        # Если сегмент пуст, пробуем глобальный поиск
        recommendations = semantic_search(request.text, top_k=3)

    return AnalyzeResponse(
        category=classification["category"],
        category_confidence=float(classification["category_confidence"]),
        subcategory=classification["subcategory"],
        subcategory_confidence=float(classification["subcategory_confidence"]),
        confidence=float(classification["confidence"]),
        entities=dict(classification["entities"]),
        products=list(classification.get("products") or []),
        recommendations=[Recommendation(**item) for item in recommendations],
    )


@app.post("/respond", response_model=RespondResponse)
def respond(request: RespondRequest) -> RespondResponse:
    try:
        answer = finalize(request.template, request.entities)
    except RateLimitError as exc:
        raise HTTPException(
            status_code=503,
            detail="Модель временно перегружена и не может сформировать ответ. Повторите попытку позже.",
        ) from exc
    if not answer:
        raise HTTPException(status_code=400, detail="Не удалось сформировать ответ.")
    return RespondResponse(answer=answer)


@app.post("/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest) -> FeedbackResponse:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    feedback_path = DATA_DIR / "feedback.jsonl"

    payload = request.model_dump()
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()

    with feedback_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return FeedbackResponse(status="сохранено")
