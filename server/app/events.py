"""
app/events.py — Server-Sent Events (SSE) formatting helpers.
"""
import json
from typing import Any, Dict


def format_sse_event(data: Dict[str, Any], event: str = "message") -> str:
    """
    Format a data dictionary into a standard SSE event format block.
    """
    data_str = json.dumps(data)
    return f"event: {event}\ndata: {data_str}\n\n"
