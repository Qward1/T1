from __future__ import annotations

from datetime import datetime
from typing import Any, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, validator


MAX_TOP_K = 10
DEFAULT_TOP_K = 3
MAX_COMMENT_LENGTH = 500


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100_000)
    top_k: int = Field(DEFAULT_TOP_K, ge=1, le=MAX_TOP_K)
    session_id: Optional[str] = Field(None, max_length=128)

    @validator("query")
    def _trim_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Query must not be empty.")
        return value


class SearchResult(BaseModel):
    id: int
    title: str
    snippet: str
    score: float
    category: Optional[str] = None
    subcategory: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]
    latency_ms: float


class SpellCheckRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100_000)
    session_id: Optional[str] = Field(None, max_length=128)

    @validator("text")
    def _trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Text must not be empty.")
        return value


class SpellCheckResponse(BaseModel):
    corrected: str


class ClassifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100_000)
    session_id: Optional[str] = Field(None, max_length=128)

    @validator("text")
    def _trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Text must not be empty.")
        return value


class ClassifyResponse(BaseModel):
    label: str
    confidence: float
    raw: Any


class FeedbackRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100_000)
    item_id: Optional[int] = None
    useful: bool
    comment: Optional[str] = Field(None, max_length=MAX_COMMENT_LENGTH)
    session_id: Optional[str] = Field(None, max_length=128)

    @validator("query")
    def _trim_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Query must not be empty.")
        return value

    @validator("comment")
    def _normalize_comment(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if value else value


class FeedbackResponse(BaseModel):
    ok: bool = True


class MessageFeedbackRequest(BaseModel):
    useful: bool
    session_id: Optional[str] = Field(None, max_length=128)


class ActionResponse(BaseModel):
    ok: bool = True


class StatsBucket(BaseModel):
    total: int
    success: int
    success_rate: float
    avg_latency_ms: float | None = None
    avg_score: float | None = None


class FeedbackStats(BaseModel):
    total: int
    positive: int
    negative: int
    positive_rate: float


class AccuracyBreakdown(BaseModel):
    total: int
    correct: int
    accuracy: float


class ClassificationAccuracy(BaseModel):
    templates: AccuracyBreakdown
    main: AccuracyBreakdown
    sub: AccuracyBreakdown


class ClassificationVoteRequest(BaseModel):
    category: Optional[str] = Field(None, max_length=128)
    subcategory: Optional[str] = Field(None, max_length=128)
    target: Literal["main", "sub"]
    correct: bool
    session_id: Optional[str] = Field(None, max_length=128)

    @validator("category", "subcategory")
    def _normalize_field(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        return value or None


class TemplateVoteRequest(BaseModel):
    positive: bool
    session_id: Optional[str] = Field(None, max_length=128)


class ResponseLogRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100_000)
    session_id: Optional[str] = Field(None, max_length=128)
    category: Optional[str] = Field(None, max_length=128)
    subcategory: Optional[str] = Field(None, max_length=128)
    main_vote: Optional[bool] = None
    sub_vote: Optional[bool] = None
    template_text: Optional[str] = Field(None, max_length=100_000)
    template_positive: Optional[bool] = None
    top_item_id: Optional[int] = None

    @validator("query")
    def _trim_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Query must not be empty.")
        return value

    @validator("category", "subcategory", "template_text")
    def _normalize_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        return value or None


class EventRecord(BaseModel):
    id: int
    kind: str
    timestamp: datetime
    session_id: Optional[str] = None
    detail: Optional[str] = None


class VoteBreakdown(BaseModel):
    total: int
    correct: int
    accuracy: float


class ClassificationPairStats(BaseModel):
    category: Optional[str] = None
    subcategory: Optional[str] = None
    main: VoteBreakdown
    sub: VoteBreakdown


class ClassificationQuality(BaseModel):
    overall_main: VoteBreakdown
    overall_sub: VoteBreakdown
    pairs: List[ClassificationPairStats]


class TemplateQuality(BaseModel):
    total: int
    positive: int
    negative: int
    positive_rate: float


class QualitySummary(BaseModel):
    classification: ClassificationQuality
    templates: TemplateQuality


class HistoryEntry(BaseModel):
    id: int
    timestamp: datetime
    session_id: Optional[str] = None
    query: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    main_vote: Optional[bool] = None
    sub_vote: Optional[bool] = None
    template_text: Optional[str] = None
    template_positive: Optional[bool] = None
    top_item_id: Optional[int] = None


class StatsSummary(BaseModel):
    search: StatsBucket
    classify: StatsBucket
    feedback: FeedbackStats
    recent: List[EventRecord]
    quality: QualitySummary
    history: List[HistoryEntry] = Field(default_factory=list)
    classification_accuracy: ClassificationAccuracy


class IndexRebuildResponse(BaseModel):
    ok: bool
    records: int


class ChatMessageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100_000)
    sender: Literal["client", "support"] = Field("client")
    category: Optional[str] = Field(None, max_length=128)
    subcategory: Optional[str] = Field(None, max_length=128)
    template_id: Optional[int] = None
    template_answer: Optional[str] = Field(None, max_length=100_000)
    template_source: Optional[str] = Field(None, max_length=100_000)
    session_id: Optional[str] = Field(None, max_length=128)

    @validator("text", "category", "subcategory", "template_answer", "template_source", pre=True)
    def _trim_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        return value


class ChatMessagePayload(BaseModel):
    id: int
    sender: Literal["client", "support"]
    text: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    template_answer: Optional[str] = None
    template_source: Optional[str] = None
    template_unmodified: Optional[bool] = None
    timestamp: datetime


class ChatSuggestionPayload(BaseModel):
    template_id: Optional[int] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    confidence: Optional[float] = None


class ChatMessageResponse(BaseModel):
    messages: List[ChatMessagePayload] = Field(default_factory=list)
    suggestion: Optional[ChatSuggestionPayload] = None


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessagePayload] = Field(default_factory=list)
