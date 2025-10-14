from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .classifiers import classify_and_ner
from .recommenders import DATA_DIR, finalize, rerank, retrieve

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
    audience: str
    question: str
    answer: str
    score: float


class AnalyzeResponse(BaseModel):
    category: str
    subcategory: str
    confidence: float
    entities: Dict[str, str]
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
    classification = classify_and_ner(request.text)

    candidates = retrieve(request.text, top_k=10)
    ranked = rerank(candidates, classification)
    top3 = ranked[:3]

    return AnalyzeResponse(
        category=classification["category"],
        subcategory=classification["subcategory"],
        confidence=float(classification["confidence"]),
        entities=dict(classification["entities"]),
        recommendations=[Recommendation(**item) for item in top3],
    )


@app.post("/respond", response_model=RespondResponse)
def respond(request: RespondRequest) -> RespondResponse:
    answer = finalize(request.template, request.entities)
    if not answer:
        raise HTTPException(status_code=400, detail="Unable to generate response.")
    return RespondResponse(answer=answer)


@app.post("/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest) -> FeedbackResponse:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    feedback_path = DATA_DIR / "feedback.jsonl"

    payload = request.model_dump()
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()

    with feedback_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return FeedbackResponse(status="recorded")

