from __future__ import annotations

from fastapi import APIRouter, Request

from ..models import ClassifyRequest, ClassifyResponse
from ..services.logic import handle_classify

router = APIRouter(tags=["classify"])


@router.post("/classify", response_model=ClassifyResponse)
async def classify_endpoint(payload: ClassifyRequest, request: Request) -> ClassifyResponse:
    session_header = request.headers.get("X-Session-Id")
    if session_header and not payload.session_id:
        payload.session_id = session_header[:128]

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    return handle_classify(
        payload,
        client_ip=client_ip,
        user_agent=user_agent,
    )
