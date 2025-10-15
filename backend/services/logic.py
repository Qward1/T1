from __future__ import annotations

import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import Lock
from typing import Deque, Dict, Optional

from fastapi import HTTPException, status

from ..chat_storage import (
    ChatMessage,
    delete_all_messages,
    init_chat_storage,
    list_messages,
    persist_messages,
)
from ..classifiers import classify_and_ner, detect_products
from ..models import (
    ActionResponse,
    ChatHistoryResponse,
    ChatMessagePayload,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSuggestionPayload,
    ClassifyRequest,
    ClassifyResponse,
    ClassificationVoteRequest,
    FeedbackRequest,
    FeedbackResponse,
    ResponseLogRequest,
    SearchRequest,
    SearchResponse,
    SearchResult,
    StatsSummary,
    TemplateVoteRequest,
)
from ..recommenders import preload_embeddings, semantic_search
from ..repository import fetch_categories, fetch_records_by_ids
from ..scibox_client import get_scibox_client
from ..settings import get_settings
from ..storage import (
    DATA_DIR,
    fetch_summary,
    init_storage,
    log_event,
    record_classification_vote,
    record_request_history,
    record_template_vote,
)

logger = logging.getLogger(__name__)

settings = get_settings()
init_storage()
init_chat_storage()


class RateLimiter:
    """Simple sliding window rate limiter backed by an in-memory deque."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max(1, max_requests)
        self._window = max(1, window_seconds)
        self._lock = Lock()
        self._store: Dict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: Optional[str]) -> bool:
        if not key:
            return True
        now = time.monotonic()
        with self._lock:
            bucket = self._store[key]
            while bucket and now - bucket[0] > self._window:
                bucket.popleft()
            if len(bucket) >= self._max_requests:
                return False
            bucket.append(now)
        return True


rate_limiter = RateLimiter(
    max_requests=settings.rate_limit_max_requests,
    window_seconds=settings.rate_limit_window_seconds,
)

WARMUP_PERFORMED = False


def perform_warmup() -> None:
    global WARMUP_PERFORMED
    if WARMUP_PERFORMED or not settings.warmup_enabled:
        return
    try:
        get_scibox_client()
        fetch_categories()
        preload_embeddings()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Warmup failed: %s", exc)
    else:
        WARMUP_PERFORMED = True


def _assert_rate_limit(key: Optional[str]) -> None:
    if rate_limiter.check(key):
        return
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests. Please retry later.",
    )


def _ensure_size_limit(value: str) -> None:
    if len(value.encode("utf-8")) > settings.max_request_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Request payload exceeds size limits.",
        )


def _derive_rate_key(session_id: Optional[str], client_ip: Optional[str]) -> Optional[str]:
    if session_id:
        return f"session:{session_id}"
    if client_ip:
        return f"ip:{client_ip}"
    return None


def _make_snippet(text: str, max_len: int = 280) -> str:
    snippet = (text or "").strip().replace("\n", " ")
    if len(snippet) <= max_len:
        return snippet
    return snippet[: max_len - 1].rstrip() + "…"


def _normalize_sender(value: Optional[str]) -> str:
    if value == "bot":
        return "support"
    if value == "support":
        return "support"
    if value == "client" or value == "user":
        return "client"
    return "client"


def _message_to_payload(message: ChatMessage) -> ChatMessagePayload:
    return ChatMessagePayload(
        id=message.id,
        sender=_normalize_sender(message.sender),
        text=message.text,
        category=message.category,
        subcategory=message.subcategory,
        template_answer=message.template_answer,
        timestamp=message.timestamp,
    )


def handle_search(
    request: SearchRequest,
    *,
    client_ip: Optional[str],
    user_agent: Optional[str],
) -> SearchResponse:
    perform_warmup()
    _ensure_size_limit(request.query)
    rate_key = _derive_rate_key(request.session_id, client_ip)
    _assert_rate_limit(rate_key)

    started = time.perf_counter()
    products = detect_products(request.query)
    raw_results = semantic_search(
        request.query,
        top_k=request.top_k,
        products=products,
    )
    latency_ms = (time.perf_counter() - started) * 1000

    results = [
        SearchResult(
            id=int(item["id"]),
            title=item.get("question", ""),
            snippet=_make_snippet(item.get("answer", "")),
            score=float(item.get("score", 0.0) or 0.0),
            category=item.get("category"),
            subcategory=item.get("subcategory"),
        )
        for item in raw_results
    ]

    payload = {
        "query_length": len(request.query),
        "result_count": len(results),
        "top_id": results[0].id if results else None,
        "top_score": results[0].score if results else None,
        "products": products,
    }
    log_event(
        "search",
        session_id=request.session_id,
        user_agent=user_agent,
        latency_ms=latency_ms,
        payload=payload,
        extra={"ip": client_ip} if client_ip else None,
    )

    return SearchResponse(results=results, latency_ms=round(latency_ms, 2))


def handle_classify(
    request: ClassifyRequest,
    *,
    client_ip: Optional[str],
    user_agent: Optional[str],
) -> ClassifyResponse:
    perform_warmup()
    _ensure_size_limit(request.text)
    rate_key = _derive_rate_key(request.session_id, client_ip)
    _assert_rate_limit(rate_key)

    started = time.perf_counter()
    classification = classify_and_ner(request.text)
    latency_ms = (time.perf_counter() - started) * 1000

    label_parts = [
        part
        for part in (
            classification.get("category"),
            classification.get("subcategory"),
        )
        if part
    ]
    label = " / ".join(label_parts) if label_parts else ""
    confidence = float(classification.get("confidence", 0.0) or 0.0)

    log_event(
        "classify",
        session_id=request.session_id,
        user_agent=user_agent,
        latency_ms=latency_ms,
        payload={
            "label": label,
            "confidence": confidence,
        },
        extra={"ip": client_ip} if client_ip else None,
    )

    return ClassifyResponse(label=label, confidence=confidence, raw=classification)


def handle_chat_message(
    request: ChatMessageRequest,
    *,
    client_ip: Optional[str],
    user_agent: Optional[str],
) -> ChatMessageResponse:
    text = (request.text or "").strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Text must not be empty.",
        )

    _ensure_size_limit(text)
    if request.template_answer:
        _ensure_size_limit(request.template_answer)

    rate_key = _derive_rate_key(request.session_id, client_ip)
    _assert_rate_limit(rate_key)

    sender = (request.sender or "client").strip().lower()
    timestamp = datetime.now(timezone.utc)
    saved_messages: list[ChatMessage] = []
    suggestion: Optional[ChatSuggestionPayload] = None

    if sender == "client":
        perform_warmup()
        started = time.perf_counter()
        classification = classify_and_ner(text)
        latency_ms = (time.perf_counter() - started) * 1000

        template_id = classification.get("matched_template_id")
        answer_record = None
        if template_id:
            try:
                answer_record = fetch_records_by_ids([int(template_id)]).get(int(template_id))
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to fetch template %s: %s", template_id, exc)

        fallback_answer = (
            "Извините, я пока не нашёл подходящего ответа. Пожалуйста, уточните запрос."
        )
        category = (answer_record or {}).get("category") or classification.get("category")
        subcategory = (answer_record or {}).get("subcategory") or classification.get("subcategory")
        suggested_answer = (
            (answer_record or {}).get("answer")
            or request.template_answer
            or fallback_answer
        )

        client_message = ChatMessage(
            sender="client",
            text=text,
            category=category,
            subcategory=subcategory,
            template_answer=None,
            timestamp=timestamp,
        )
        saved_messages = persist_messages([client_message])

        log_event(
            "chat",
            session_id=request.session_id,
            user_agent=user_agent,
            latency_ms=latency_ms,
            payload={
                "sender": "client",
                "category": category,
                "subcategory": subcategory,
                "template_id": template_id,
                "confidence": float(classification.get("confidence", 0.0) or 0.0),
            },
            extra={"ip": client_ip} if client_ip else None,
        )

        logger.info(
            "Client message recorded category=%s subcategory=%s template_id=%s confidence=%.3f",
            category,
            subcategory,
            template_id,
            float(classification.get("confidence", 0.0) or 0.0),
        )
    elif sender == "support":
        support_message = ChatMessage(
            sender="support",
            text=text,
            category=request.category,
            subcategory=request.subcategory,
            template_answer=request.template_answer or text,
            timestamp=timestamp,
        )
        saved_messages = persist_messages([support_message])

        log_event(
            "chat",
            session_id=request.session_id,
            user_agent=user_agent,
            payload={
                "sender": "support",
                "category": request.category,
                "subcategory": request.subcategory,
            },
            extra={"ip": client_ip} if client_ip else None,
        )

        logger.info(
            "Support reply stored category=%s subcategory=%s",
            request.category,
            request.subcategory,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported sender.",
        )

    payload_messages = [_message_to_payload(message) for message in saved_messages]
    return ChatMessageResponse(messages=payload_messages, suggestion=suggestion)


def handle_chat_history() -> ChatHistoryResponse:
    messages = [_message_to_payload(item) for item in list_messages()]
    return ChatHistoryResponse(messages=messages)


def handle_chat_clear() -> ActionResponse:
    delete_all_messages()
    logger.info("Chat history cleared by operator.")
    return ActionResponse()


def handle_feedback(
    request: FeedbackRequest,
    *,
    client_ip: Optional[str],
    user_agent: Optional[str],
) -> FeedbackResponse:
    _ensure_size_limit(request.query)
    if request.comment:
        _ensure_size_limit(request.comment)
    rate_key = _derive_rate_key(request.session_id, client_ip)
    _assert_rate_limit(rate_key)

    record = request.model_dump()
    record["timestamp"] = datetime.now(timezone.utc).isoformat()
    record["user_agent"] = user_agent or ""
    record["client_ip"] = client_ip or ""

    feedback_path = DATA_DIR / "feedback.jsonl"
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    with feedback_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        fh.flush()

    log_event(
        "feedback",
        session_id=request.session_id,
        user_agent=user_agent,
        payload={
            "useful": bool(request.useful),
            "item_id": request.item_id,
        },
        extra={"ip": client_ip} if client_ip else None,
    )

    return FeedbackResponse()


def handle_classification_vote(
    request: ClassificationVoteRequest,
    *,
    client_ip: Optional[str],
    user_agent: Optional[str],
) -> ActionResponse:
    rate_key = _derive_rate_key(request.session_id, client_ip)
    _assert_rate_limit(rate_key)

    record_classification_vote(
        category=request.category,
        subcategory=request.subcategory,
        target=request.target,
        is_correct=request.correct,
        session_id=request.session_id,
    )

    log_event(
        "classification_vote",
        session_id=request.session_id,
        user_agent=user_agent,
        payload={
            "category": request.category,
            "subcategory": request.subcategory,
            "target": request.target,
            "correct": bool(request.correct),
        },
        extra={"ip": client_ip} if client_ip else None,
    )

    return ActionResponse()


def handle_template_vote(
    request: TemplateVoteRequest,
    *,
    client_ip: Optional[str],
    user_agent: Optional[str],
) -> ActionResponse:
    rate_key = _derive_rate_key(request.session_id, client_ip)
    _assert_rate_limit(rate_key)

    record_template_vote(
        is_positive=request.positive,
        session_id=request.session_id,
    )

    log_event(
        "template_vote",
        session_id=request.session_id,
        user_agent=user_agent,
        payload={"positive": bool(request.positive)},
        extra={"ip": client_ip} if client_ip else None,
    )

    return ActionResponse()


def handle_response_submission(
    request: ResponseLogRequest,
    *,
    client_ip: Optional[str],
    user_agent: Optional[str],
) -> ActionResponse:
    _ensure_size_limit(request.query)
    if request.template_text:
        _ensure_size_limit(request.template_text)
    rate_key = _derive_rate_key(request.session_id, client_ip)
    _assert_rate_limit(rate_key)

    record_request_history(
        query=request.query,
        session_id=request.session_id,
        category=request.category,
        subcategory=request.subcategory,
        main_vote=request.main_vote,
        sub_vote=request.sub_vote,
        template_text=request.template_text,
        template_positive=request.template_positive,
        top_item_id=request.top_item_id,
    )

    log_event(
        "response",
        session_id=request.session_id,
        user_agent=user_agent,
        payload={
            "has_template": bool(request.template_text),
            "template_positive": request.template_positive,
            "main_vote": request.main_vote,
            "sub_vote": request.sub_vote,
            "category": request.category,
            "subcategory": request.subcategory,
        },
        extra={"ip": client_ip} if client_ip else None,
    )

    return ActionResponse()


def read_stats_summary() -> StatsSummary:
    summary = fetch_summary()
    return StatsSummary(
        search=summary["search"],
        classify=summary["classify"],
        feedback=summary["feedback"],
        recent=summary["recent"],
        quality=summary["quality"],
        history=summary["history"],
        classification_accuracy=summary["classification_accuracy"],
    )
