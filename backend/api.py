from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import classify, feedback, index, quality, search, stats
from .services.logic import perform_warmup
from .settings import get_settings

settings = get_settings()

app = FastAPI(title="FAQ Assistant API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.frontend_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/api")
app.include_router(classify.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(quality.router, prefix="/api")
app.include_router(index.router, prefix="/api")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event() -> None:  # pragma: no cover - framework integration
    perform_warmup()
