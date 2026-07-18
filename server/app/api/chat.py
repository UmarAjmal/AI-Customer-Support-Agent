"""
app/api/chat.py — Streaming chat endpoint using Server Sent Events (SSE).
Streams generated response tokens sequentially for high responsiveness.
"""
import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
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
    Uses SSE (text/event-stream format).
    """
    async def sse_generator() -> AsyncGenerator[str, None]:
        try:
            # 1. Run the agent logic to fetch the synthesized response
            # Note: In a larger app we can stream directly from HuggingFace chunks,
            # but to ensure database checks compile successfully in the LangGraph state machine,
            # we run the graph fully and stream the output tokens with minimal delay (typing simulation).
            response_text = await agent_service.run_agent(
                db=db,
                session_key=req.session_key,
                user_message=req.message
            )

            # 2. Yield tokens sequentially to recreate a typing effect
            # Split by words to keep it fluent
            words = response_text.split(" ")
            for i, word in enumerate(words):
                # Add spacing back
                chunk = word + (" " if i < len(words) - 1 else "")
                
                # Format SSE payload matching frontend parsing structure
                data = {
                    "token": chunk,
                    "done": i == len(words) - 1
                }
                yield f"data: {json.dumps(data)}\n\n"
                
                # Dynamic pacing (fast typing effect)
                await asyncio.sleep(0.04)

        except Exception as e:
            # Yield error event
            err_data = {"error": str(e), "done": True}
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
