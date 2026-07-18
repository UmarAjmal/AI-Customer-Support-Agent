"""
app/ai/memory.py — Chat memory management helpers for the AI agent.
"""
from typing import Any, Dict, List


def format_chat_history(messages: List[Dict[str, Any]], max_turns: int = 5) -> str:
    """
    Format a list of chat message dictionaries into a readable string prompt context.
    Truncates history to the latest N turns to fit context window limits.
    """
    formatted = []
    # Take only last N messages
    recent_msgs = messages[-max_turns * 2:] if max_turns > 0 else messages
    
    for msg in recent_msgs:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "").strip()
        formatted.append(f"{role}: {content}")
        
    return "\n".join(formatted)
