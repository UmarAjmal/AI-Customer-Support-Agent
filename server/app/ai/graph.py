"""
app/ai/graph.py — ShopEase LangGraph Supervisor (Captain) and worker team workflow.
"""
from typing import Any, Dict, Literal
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.graph import StateGraph, START, END

from app.ai.nodes import (
    AgentState,
    supervisor_node,
    product_agent_node,
    order_agent_node,
    faq_agent_node,
)


def compile_agent_graph(db: AsyncSession):
    """
    Supervisor / Captain Architecture:
      START → supervisor (Captain decides routing)
            → PRODUCT_AGENT (worker) → END
            → ORDER_AGENT (worker) → END
            → FAQ_AGENT (worker) → END
            → FINISH (Supervisor directly responded) → END
    """
    builder = StateGraph(AgentState)

    # 1. Add supervisor node
    builder.add_node("supervisor", supervisor_node)

    # 2. Add worker wrappers to bind db session
    async def product_agent_wrapper(state: AgentState) -> Dict[str, Any]:
        return await product_agent_node(state, db)

    async def order_agent_wrapper(state: AgentState) -> Dict[str, Any]:
        return await order_agent_node(state, db)

    async def faq_agent_wrapper(state: AgentState) -> Dict[str, Any]:
        return await faq_agent_node(state, db)

    builder.add_node("product_agent", product_agent_wrapper)
    builder.add_node("order_agent", order_agent_wrapper)
    builder.add_node("faq_agent", faq_agent_wrapper)

    # 3. Routing edge logic from Supervisor
    def route_from_supervisor(state: AgentState) -> Literal["product_agent", "order_agent", "faq_agent", "__end__"]:
        next_agent = state.get("next_agent", "FINISH")
        if next_agent == "PRODUCT_AGENT":
            return "product_agent"
        if next_agent == "ORDER_AGENT":
            return "order_agent"
        if next_agent == "FAQ_AGENT":
            return "faq_agent"
        return "__end__"

    # 4. Bind edges
    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "product_agent": "product_agent",
            "order_agent": "order_agent",
            "faq_agent": "faq_agent",
            "__end__": END,
        },
    )
    builder.add_edge("product_agent", END)
    builder.add_edge("order_agent", END)
    builder.add_edge("faq_agent", END)

    return builder.compile()
