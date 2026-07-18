"""
app/api/chat.py — Streaming chat endpoint using Server Sent Events (SSE).

Security layers:
  1. Rate limiting: 20 req/min per IP (sliding window, no Redis needed)
  2. Session validation: HMAC-signed session_key prevents anonymous abuse

Protocol:
  GET  /api/chat/session           → returns a signed session_key
  POST /api/chat/stream            → requires valid session_key + rate limit

SSE stream format:
  {"type":"typing","done":false}            -- typing indicator
  {"type":"token","token":"...","done":false} -- word-by-word stream
  {"type":"done","suggestions":[...]}       -- final event with quick replies
"""
import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.rate_limiter import make_rate_limit_dep
from app.core.session_auth import generate_session_key, validate_session_key
from app.database import schemas
from app.services import agent_service

router = APIRouter(prefix="/chat", tags=["Chat AI Agent"])

# Rate limit: 20 chat requests per IP per 60 seconds
_chat_rate_limit = make_rate_limit_dep(max_requests=20, window_seconds=60, label="chat")

# Stricter limit for session generation: 10 new sessions per IP per minute
_session_rate_limit = make_rate_limit_dep(max_requests=10, window_seconds=60, label="session")


@router.get("/session")
async def get_chat_session(
    request: Request,
    _: None = Depends(_session_rate_limit),
):
    """
    Issue a new HMAC-signed session key for the chat widget.
    The client must use this key in all subsequent /chat/stream requests.
    Sessions are stateless — no DB write needed.
    """
    key = generate_session_key(prefix="ses")
    return JSONResponse(content={"session_key": key})


@router.post("/stream")
async def chat_stream(
    request: Request,
    req: schemas.ChatStreamRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_chat_rate_limit),
):
    """
    Handle customer message and stream response tokens via SSE.
    Validates HMAC-signed session_key before processing any query.
    """
    # Validate session key (raises 401 if forged/missing)
    validate_session_key(req.session_key)

    async def sse_generator() -> AsyncGenerator[str, None]:
        try:
            # 1. Fire typing indicator immediately
            typing_event = {"type": "typing", "done": False}
            yield f"data: {json.dumps(typing_event)}\n\n"
            await asyncio.sleep(0.05)

            # 2. Run agent
            response_text, suggestions = await agent_service.run_agent(
                db=db,
                session_key=req.session_key,
                user_message=req.message
            )

            # 3. Stream word-by-word
            words = response_text.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                data = {"type": "token", "token": chunk, "done": False}
                yield f"data: {json.dumps(data)}\n\n"
                await asyncio.sleep(0.04)

            # 4. Final done event with quick-reply suggestions
            done_data = {"type": "done", "done": True, "suggestions": suggestions or []}
            yield f"data: {json.dumps(done_data)}\n\n"

        except Exception as e:
            err_data = {"type": "error", "error": str(e), "done": True}
            yield f"data: {json.dumps(err_data)}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
