"""
app/api/chat.py — Streaming chat endpoint using Server Sent Events (SSE).
Streams generated response tokens sequentially for high responsiveness.
Includes typing indicator and contextual quick-reply suggestions.
"""
import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.database import schemas
from app.services import agent_service

router = APIRouter(prefix="/chat", tags=["Chat AI Agent"])


@router.post("/stream")
async def chat_stream(
    req: schemas.ChatStreamRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle customer message and yield a stream of tokens using Server Sent Events.
    Protocol:
      1. {\"type\":\"typing\",\"done\":false}           — typing indicator
      2. {\"type\":\"token\",\"token\":\"...\",\"done\":false} — streaming tokens
      3. {\"type\":\"done\",\"suggestions\":[...]}      — final event with quick replies
    """
    async def sse_generator() -> AsyncGenerator[str, None]:
        try:
            # 1. Fire typing indicator immediately so frontend can show spinner
            typing_event = {"type": "typing", "done": False}
            yield f"data: {json.dumps(typing_event)}\n\n"
            await asyncio.sleep(0.05)

            # 2. Run the agent logic — returns (response_text, suggestions)
            response_text, suggestions = await agent_service.run_agent(
                db=db,
                session_key=req.session_key,
                user_message=req.message
            )

            # 3. Yield tokens sequentially to recreate a typing effect
            words = response_text.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                data = {
                    "type": "token",
                    "token": chunk,
                    "done": False,
                }
                yield f"data: {json.dumps(data)}\n\n"
                await asyncio.sleep(0.04)

            # 4. Final done event with contextual quick-reply suggestions
            done_data = {
                "type": "done",
                "done": True,
                "suggestions": suggestions or [],
            }
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
            "X-Accel-Buffering": "no"
        }
    )
