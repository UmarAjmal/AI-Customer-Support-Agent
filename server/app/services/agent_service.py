"""
app/services/agent_service.py — Coordinates LangGraph agent executions and handles chat session memory persistence.
Uses try/except database safety fallbacks to operate smoothly even in offline sandbox environments.
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import crud
from app.ai.graph import compile_agent_graph
from app.core.logger import get_logger

logger = get_logger(__name__)

# Simple in-memory fallback store for chat sessions when database is offline
IN_MEMORY_SESSIONS: dict = {}


async def run_agent(
    db: AsyncSession,
    session_key: str,
    user_message: str,
    user_id: Optional[UUID] = None
) -> str:
    """
    Restore chat session memory, run LangGraph intent classification + tool lookups,
    persist chat logs, and return the final AI text.
    """
    session_id = None
    history_list = []

    # 1. Fetch or initialize chat session and history (DB or In-Memory fallback)
    try:
        session = await crud.get_or_create_chat_session(db, session_key)
        session_id = session.id
        for msg in session.messages:
            history_list.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # Save user message to database
        await crud.add_chat_message(
            db=db,
            session_id=session.id,
            role="user",
            content=user_message
        )
    except Exception as e:
        logger.warning("agent_service.db_load_error", error=str(e), message="Falling back to in-memory session.")
        
        # Load from in-memory cache
        if session_key not in IN_MEMORY_SESSIONS:
            IN_MEMORY_SESSIONS[session_key] = []
        
        for msg in IN_MEMORY_SESSIONS[session_key]:
            history_list.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
            
        # Add user message to in-memory cache
        IN_MEMORY_SESSIONS[session_key].append({
            "role": "user",
            "content": user_message
        })

    # 2. Compile and execute LangGraph
    agent_flow = compile_agent_graph(db)
    
    initial_state = {
        "message": user_message,
        "history": history_list,
        "intent": "GENERAL_CHAT",
        "db_results": None,
        "response": "",
        "session_key": session_key
    }

    logger.info("agent.execution_started", session_key=session_key)
    result = await agent_flow.ainvoke(initial_state)
    logger.info("agent.execution_completed", session_key=session_key, intent=result.get("intent"))

    ai_response = result.get("response", "I'm sorry, I'm having trouble processing that right now.")

    # 3. Save assistant response to DB or In-Memory fallback
    if session_id:
        try:
            await crud.add_chat_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=ai_response
            )
        except Exception as e:
            logger.warning("agent_service.db_save_reply_error", error=str(e))
    else:
        # Save reply in in-memory cache
        IN_MEMORY_SESSIONS[session_key].append({
            "role": "assistant",
            "content": ai_response
        })

    return ai_response
