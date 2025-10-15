from __future__ import annotations

from fastapi import APIRouter, Request

from ..models import SearchRequest, SearchResponse
from ..services.logic import handle_search

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search_endpoint(payload: SearchRequest, request: Request) -> SearchResponse:
    session_header = request.headers.get("X-Session-Id")
    if session_header and not payload.session_id:
        payload.session_id = session_header[:128]

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    return handle_search(
        payload,
        client_ip=client_ip,
        user_agent=user_agent,
    )
