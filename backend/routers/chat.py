from __future__ import annotations

from fastapi import APIRouter, Request

from ..models import ActionResponse, ChatHistoryResponse, ChatMessageRequest, ChatMessageResponse
from ..services.logic import handle_chat_clear, handle_chat_history, handle_chat_message

router = APIRouter(tags=["chat"])


@router.get("/messages", response_model=ChatHistoryResponse)
async def get_messages() -> ChatHistoryResponse:
    return handle_chat_history()


@router.post("/message", response_model=ChatMessageResponse)
async def post_message(request: Request, payload: ChatMessageRequest) -> ChatMessageResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return handle_chat_message(payload, client_ip=client_ip, user_agent=user_agent)


@router.delete("/messages", response_model=ActionResponse)
async def clear_messages() -> ActionResponse:
    return handle_chat_clear()
