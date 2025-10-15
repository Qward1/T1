from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from ..build_index import build_faq_index
from ..models import IndexRebuildResponse
from ..recommenders import refresh_embeddings
from ..settings import get_settings

router = APIRouter(tags=["index"])


@router.post("/index/rebuild", response_model=IndexRebuildResponse)
async def rebuild_index(request: Request) -> IndexRebuildResponse:
    settings = get_settings()
    if not settings.admin_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint disabled")

    token = request.headers.get("X-Admin-Token")
    if token != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")

    if not settings.faq_source_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FAQ source path is not configured.",
        )

    try:
        records = build_faq_index()
        refresh_embeddings()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rebuild index: {exc}",
        ) from exc

    return IndexRebuildResponse(ok=True, records=records)
