"""Agent orchestration runtime and real-time SSE telemetry streamer."""

import json
import time
import uuid
from datetime import date, datetime, timezone
from typing import Any, AsyncGenerator

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from backend.config import get_chat_model, logger, settings
from backend.mcp_client import mcp_manager

# Shared in-memory checkpointer for multi-turn conversations
checkpointer = MemorySaver()


def _format_sse(event_type: str, data: dict[str, Any]) -> str:
    """Formats a Server-Sent Event payload according to W3C SSE specification."""
    json_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {json_data}\n\n"


def _now_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _extract_tool_output_text(output: Any) -> str:
    """Extracts clean human-readable text from various LangChain/FastMCP tool output formats."""
    import re
    if isinstance(output, str):
        # Handle stringified Python list/dict containing 'text': '...'
        if output.startswith("[") and "'text':" in output:
            match = re.search(r"'text':\s*'(.*?)'(?:,\s*'id'|\})", output, re.DOTALL)
            if match:
                return match.group(1).replace("\\n", "\n")
        return output
    if isinstance(output, ToolMessage):
        return str(output.content)
    if isinstance(output, list):
        parts = []
        for item in output:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            elif hasattr(item, "content"):
                parts.append(str(item.content))
            elif hasattr(item, "text"):
                parts.append(str(item.text))
            else:
                parts.append(str(item))
        return "\n".join(parts) if parts else str(output)
    if isinstance(output, dict):
        if "text" in output:
            return str(output["text"])
        return json.dumps(output)
    return str(output)

async def stream_agent_lifecycle(
    message: str,
    thread_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> AsyncGenerator[str, None]:
    """Executes the agent and streams granular observability telemetry & tokens over SSE.

    Args:
        message: The user prompt.
        thread_id: Optional thread ID for conversation memory continuity.
        provider: Optional LLM provider override.
        model: Optional model identifier override.
        api_key: Optional client-supplied API key.
        base_url: Optional custom base URL.

    Yields:
        Formatted SSE event strings.
    """
    start_time = time.perf_counter()
    session_thread_id = thread_id or str(uuid.uuid4())
    active_provider = provider or settings.default_provider
    tools_invoked: list[str] = []
    tool_start_times: dict[str, float] = {}

    try:
        # Step 1: Lifecycle Start & Dynamic Model Resolution
        llm = get_chat_model(
            provider=active_provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
        resolved_model_name = getattr(llm, "model_name", None) or getattr(llm, "model", model or "default")

        yield _format_sse(
            "lifecycle_start",
            {
                "thread_id": session_thread_id,
                "provider": active_provider,
                "model": resolved_model_name,
                "timestamp": _now_iso(),
            },
        )

        # Step 2: Context Building & MCP Resource Injection
        yield _format_sse(
            "pipeline_step",
            {
                "step": "prompt_context",
                "title": "Context & MCP Resource Injection",
                "details": "Reading categories://list and injecting current date & taxonomy into system prompt.",
                "timestamp": _now_iso(),
            },
        )

        async with mcp_manager.session() as mcp_session:
            tools = await mcp_manager.get_tools(session=mcp_session)
            categories_json = await mcp_manager.get_categories_resource(session=mcp_session)

            today_str = date.today().isoformat()
            system_prompt = (
                "You are SpendWise AI, an expert agentic financial assistant.\n"
                "You have direct access to tools for managing expenses, setting budgets, checking budget health, and generating financial summaries.\n\n"
                f"Today's date is: {today_str}.\n"
                f"Valid Category Taxonomy:\n{categories_json}\n\n"
                "Guidelines:\n"
                "- When the user asks to log, add, edit, or delete an expense, call the appropriate tool.\n"
                "- When the user asks about budgets or summaries, use check_budget or summarize.\n"
                "- Always provide clear, helpful, and concise markdown answers with currency formatting ($XX.XX).\n"
            )

            # Step 3: LLM Model Reasoning Phase
            yield _format_sse(
                "pipeline_step",
                {
                    "step": "llm_reasoning",
                    "title": "LLM Reasoning & Tool Selection",
                    "details": f"Model {resolved_model_name} evaluating user prompt with {len(tools)} loaded MCP tools.",
                    "timestamp": _now_iso(),
                },
            )

            agent = create_agent(
                model=llm,
                tools=tools,
                checkpointer=checkpointer,
                system_prompt=system_prompt,
            )

            # Stream LangGraph events
            async for event in agent.astream_events(
                {"messages": [HumanMessage(content=message)]},
                version="v2",
                config={"configurable": {"thread_id": session_thread_id}},
            ):
                event_kind = event.get("event")
                name = event.get("name", "")

                # Tool execution started
                if event_kind == "on_tool_start":
                    tool_name = name
                    tools_invoked.append(tool_name)
                    tool_input = event.get("data", {}).get("input", {})
                    run_id = event.get("run_id", str(uuid.uuid4()))
                    tool_start_times[run_id] = time.perf_counter()

                    jsonrpc_packet = {
                        "jsonrpc": "2.0",
                        "id": run_id[:8],
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": tool_input,
                        },
                    }

                    yield _format_sse(
                        "tool_start",
                        {
                            "step": "mcp_dispatch",
                            "tool": tool_name,
                            "input": tool_input,
                            "run_id": run_id,
                            "jsonrpc": jsonrpc_packet,
                            "timestamp": _now_iso(),
                        },
                    )

                # Tool execution completed
                elif event_kind == "on_tool_end":
                    tool_name = name
                    raw_output = event.get("data", {}).get("output", "")
                    output_text = _extract_tool_output_text(raw_output)
                    run_id = event.get("run_id", "")
                    duration_ms = 0
                    if run_id in tool_start_times:
                        duration_ms = int((time.perf_counter() - tool_start_times[run_id]) * 1000)

                    jsonrpc_response = {
                        "jsonrpc": "2.0",
                        "id": run_id[:8] if run_id else "0",
                        "result": {
                            "content": [{"type": "text", "text": output_text}],
                        },
                    }

                    yield _format_sse(
                        "tool_end",
                        {
                            "step": "mcp_dispatch",
                            "tool": tool_name,
                            "output": output_text,
                            "duration_ms": duration_ms,
                            "run_id": run_id,
                            "jsonrpc": jsonrpc_response,
                            "timestamp": _now_iso(),
                        },
                    )

                # Streamed token from chat model
                elif event_kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and isinstance(chunk.content, str) and chunk.content:
                        yield _format_sse(
                            "token",
                            {
                                "delta": chunk.content,
                                "timestamp": _now_iso(),
                            },
                        )

        # Step 4: Synthesis & Finalization
        yield _format_sse(
            "pipeline_step",
            {
                "step": "synthesis",
                "title": "Response Synthesis",
                "details": "Agent synthesis complete.",
                "timestamp": _now_iso(),
            },
        )

        total_elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        yield _format_sse(
            "done",
            {
                "thread_id": session_thread_id,
                "tools_invoked": tools_invoked,
                "total_duration_ms": total_elapsed_ms,
                "timestamp": _now_iso(),
            },
        )

    except Exception as e:
        logger.exception("Error during agent streaming execution: %s", e)
        yield _format_sse(
            "error",
            {
                "error": str(e),
                "timestamp": _now_iso(),
            },
        )
