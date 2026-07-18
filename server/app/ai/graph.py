"""
app/ai/graph.py — ShopEase LangGraph workflow with early exit for off-topic.
"""
from typing import Any, Dict, Literal
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.graph import StateGraph, START, END

from app.ai.nodes import (
    AgentState,
    detect_intent_node,
    query_db_node,
    generate_response_node,
)


def compile_agent_graph(db: AsyncSession):
    """
    Flow:
      START → detect_intent
            → (OFF_TOPIC / HUMAN / GENERAL) skip DB → generate_response → END
            → (shop intents) query_db → generate_response → END
    """
    builder = StateGraph(AgentState)

    builder.add_node("detect_intent", detect_intent_node)

    async def query_db_wrapper(state: AgentState) -> Dict[str, Any]:
        return await query_db_node(state, db)

    builder.add_node("query_db", query_db_wrapper)
    builder.add_node("generate_response", generate_response_node)

    def route_after_intent(state: AgentState) -> Literal["query_db", "generate_response"]:
        intent = state.get("intent", "GENERAL_CHAT")
        if intent in ["OFF_TOPIC", "HUMAN_SUPPORT", "GENERAL_CHAT"]:
            return "generate_response"
        return "query_db"

    builder.add_edge(START, "detect_intent")
    builder.add_conditional_edges(
        "detect_intent",
        route_after_intent,
        {
            "query_db": "query_db",
            "generate_response": "generate_response",
        },
    )
    builder.add_edge("query_db", "generate_response")
    builder.add_edge("generate_response", END)

    return builder.compile()
