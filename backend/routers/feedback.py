from __future__ import annotations

from fastapi import APIRouter, Request

from ..models import FeedbackRequest, FeedbackResponse
from ..services.logic import handle_feedback

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback_endpoint(payload: FeedbackRequest, request: Request) -> FeedbackResponse:
    session_header = request.headers.get("X-Session-Id")
    if session_header and not payload.session_id:
        payload.session_id = session_header[:128]

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    return handle_feedback(
        payload,
        client_ip=client_ip,
        user_agent=user_agent,
    )
