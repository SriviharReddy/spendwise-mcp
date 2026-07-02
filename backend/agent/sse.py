"""Server-Sent Events (SSE) and JSON-RPC telemetry formatting utilities."""

import json
from datetime import datetime, timezone
from typing import Any


def format_sse(event_type: str, data: dict[str, Any]) -> str:
    """Formats a payload into a W3C-compliant Server-Sent Event frame."""
    json_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {json_data}\n\n"


def now_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def build_jsonrpc_call_packet(
    tool_name: str,
    tool_input: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    """Constructs a simulated JSON-RPC 2.0 request frame for observability."""
    return {
        "jsonrpc": "2.0",
        "id": run_id[:8] if run_id else "1",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": tool_input,
        },
    }


def build_jsonrpc_response_packet(
    output_text: str,
    run_id: str,
) -> dict[str, Any]:
    """Constructs a simulated JSON-RPC 2.0 response frame for observability."""
    return {
        "jsonrpc": "2.0",
        "id": run_id[:8] if run_id else "1",
        "result": {
            "content": [{"type": "text", "text": output_text}],
        },
    }
