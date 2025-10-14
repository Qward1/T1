from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import RateLimitError
from pydantic import BaseModel, Field

from .classifiers import classify_and_ner
from .recommenders import DATA_DIR, finalize, semantic_search
from .storage import (
    get_classification_stats,
    get_recent_history,
    get_template_stats,
    init_stats_db,
    record_classification_feedback,
    record_request_history,
    record_template_feedback,
)

app = FastAPI(title="Smart Support Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_stats_db()


class ClassificationStat(BaseModel):
    category: str
    subcategory: str
    correct: int
    incorrect: int
    accuracy: float


class TemplateStats(BaseModel):
    positive: int
    negative: int
    accuracy: float


class HistoryItem(BaseModel):
    id: int
    query: str
    category: str
    subcategory: str
    template_id: int | None = None
    final_answer: str
    created_at: str


class AnalyticsResponse(BaseModel):
    classification: List[ClassificationStat]
    template: TemplateStats
    history: List[HistoryItem]


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
    answer: str
    entities: Dict[str, str]
    alternatives: List[Recommendation]
    trace: Dict[str, float | bool]


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


class ClassificationFeedbackRequest(BaseModel):
    category: str
    subcategory: str
    is_correct: bool


class TemplateFeedbackRequest(BaseModel):
    is_positive: bool


class HistoryRequest(BaseModel):
    query: str
    category: str | None = None
    subcategory: str | None = None
    template_id: int | None = None
    final_answer: str


def _build_analytics_response() -> AnalyticsResponse:
    classification_stats = [ClassificationStat(**row) for row in get_classification_stats()]
    template_stats = TemplateStats(**get_template_stats())
    history_items = [HistoryItem(**row) for row in get_recent_history()]
    return AnalyticsResponse(
        classification=classification_stats,
        template=template_stats,
        history=history_items,
    )


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
            detail="Модель временно недоступна из-за лимита запросов. Повторите попытку чуть позже.",
        ) from exc

    start_time = datetime.now()

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
        recommendations = semantic_search(request.text, top_k=3)
        used_fallback = True
    else:
        used_fallback = not use_segment

    answer = ""
    if recommendations:
        top_template = recommendations[0]
        answer = finalize(top_template["answer"], classification["entities"])

    latency_ms = (datetime.now() - start_time).total_seconds() * 1000

    alternatives = [
        Recommendation(
            id=item["id"],
            category=item["category"],
            subcategory=item["subcategory"],
            audience=item.get("audience"),
            question=item["question"],
            answer=item["answer"],
            score=item.get("score", 0.0),
        )
        for item in recommendations
    ]

    return AnalyzeResponse(
        category=classification["category"],
        category_confidence=float(classification["category_confidence"]),
        subcategory=classification["subcategory"],
        subcategory_confidence=float(classification["subcategory_confidence"]),
        confidence=float(classification["confidence"]),
        answer=answer,
        entities=dict(classification["entities"]),
        alternatives=alternatives,
        trace={
            "used_fallback": used_fallback,
            "latency_ms": round(latency_ms, 2),
        },
    )


@app.post("/respond", response_model=RespondResponse)
def respond(request: RespondRequest) -> RespondResponse:
    try:
        answer = finalize(request.template, request.entities)
    except RateLimitError as exc:
        raise HTTPException(
            status_code=503,
            detail="Модель перегружена и не смогла сформировать ответ. Повторите попытку позже.",
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


@app.post("/metrics/classification", response_model=AnalyticsResponse)
def classification_feedback(request: ClassificationFeedbackRequest) -> AnalyticsResponse:
    record_classification_feedback(request.category, request.subcategory, request.is_correct)
    return _build_analytics_response()


@app.post("/metrics/template", response_model=AnalyticsResponse)
def template_feedback(request: TemplateFeedbackRequest) -> AnalyticsResponse:
    record_template_feedback(request.is_positive)
    return _build_analytics_response()


@app.post("/history", response_model=AnalyticsResponse)
def history(request: HistoryRequest) -> AnalyticsResponse:
    record_request_history(
        request.query,
        request.category,
        request.subcategory,
        request.template_id,
        request.final_answer,
    )
    return _build_analytics_response()


@app.get("/analytics", response_model=AnalyticsResponse)
def analytics() -> AnalyticsResponse:
    return _build_analytics_response()
