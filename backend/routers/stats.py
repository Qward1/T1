from __future__ import annotations

from fastapi import APIRouter

from ..models import StatsSummary
from ..services.logic import read_stats_summary

router = APIRouter(tags=["stats"])


@router.get("/stats/summary", response_model=StatsSummary)
async def stats_summary() -> StatsSummary:
    return read_stats_summary()
