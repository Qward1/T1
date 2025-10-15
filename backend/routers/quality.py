from __future__ import annotations

from fastapi import APIRouter, Request

from ..models import (
    ActionResponse,
    ClassificationVoteRequest,
    ResponseLogRequest,
    TemplateVoteRequest,
)
from ..services.logic import (
    handle_classification_vote,
    handle_response_submission,
    handle_template_vote,
)

router = APIRouter(tags=["quality"])


@router.post("/quality/classification", response_model=ActionResponse)
async def classification_vote_endpoint(
    payload: ClassificationVoteRequest,
    request: Request,
) -> ActionResponse:
    session_header = request.headers.get("X-Session-Id")
    if session_header and not payload.session_id:
        payload.session_id = session_header[:128]

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    return handle_classification_vote(
        payload,
        client_ip=client_ip,
        user_agent=user_agent,
    )


@router.post("/quality/template", response_model=ActionResponse)
async def template_vote_endpoint(
    payload: TemplateVoteRequest,
    request: Request,
) -> ActionResponse:
    session_header = request.headers.get("X-Session-Id")
    if session_header and not payload.session_id:
        payload.session_id = session_header[:128]

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    return handle_template_vote(
        payload,
        client_ip=client_ip,
        user_agent=user_agent,
    )


@router.post("/history", response_model=ActionResponse)
async def response_history_endpoint(
    payload: ResponseLogRequest,
    request: Request,
) -> ActionResponse:
    session_header = request.headers.get("X-Session-Id")
    if session_header and not payload.session_id:
        payload.session_id = session_header[:128]

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    return handle_response_submission(
        payload,
        client_ip=client_ip,
        user_agent=user_agent,
    )
