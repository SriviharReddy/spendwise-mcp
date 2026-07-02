"""Unit tests for the modular backend.agent package."""

from langchain_core.messages import ToolMessage
from backend.agent.prompts import build_system_prompt
from backend.agent.sse import (
    build_jsonrpc_call_packet,
    build_jsonrpc_response_packet,
    format_sse,
    now_iso,
)
from backend.agent.tools import extract_tool_output_text


def test_build_system_prompt():
    """Tests system prompt generation and dynamic resource injection."""
    categories_json = '{"categories": ["Food", "Travel", "Housing"]}'
    prompt = build_system_prompt(categories_json, today_str="2026-08-25")

    assert "Today's date is: 2026-08-25" in prompt
    assert "Valid Category Taxonomy:" in prompt
    assert '{"categories": ["Food", "Travel", "Housing"]}' in prompt
    assert "SpendWise AI" in prompt


def test_extract_tool_output_text_formats():
    """Tests extracting human-readable text from various output payload types."""
    # 1. Plain string
    assert extract_tool_output_text("Success: Expense recorded") == "Success: Expense recorded"

    # 2. ToolMessage instance
    msg = ToolMessage(content="Budget updated", tool_call_id="call_1")
    assert extract_tool_output_text(msg) == "Budget updated"

    # 3. List of dicts with text
    list_dicts = [{"type": "text", "text": "=== EXPENSE SUMMARY ==="}]
    assert extract_tool_output_text(list_dicts) == "=== EXPENSE SUMMARY ==="

    # 4. Stringified python list representation
    stringified_list = "[{'type': 'text', 'text': '=== EXPENSE SUMMARY ===\\nFrom: 2026-08-01', 'id': 'lc_123'}]"
    extracted = extract_tool_output_text(stringified_list)
    assert "=== EXPENSE SUMMARY ===" in extracted
    assert "From: 2026-08-01" in extracted

    # 5. Plain dict
    dict_payload = {"text": "Formatted result"}
    assert extract_tool_output_text(dict_payload) == "Formatted result"


def test_sse_and_jsonrpc_formatters():
    """Tests SSE frame encoding and JSON-RPC wire simulation packet generation."""
    # SSE formatting
    frame = format_sse("token", {"delta": "Hello world"})
    assert frame == 'event: token\ndata: {"delta": "Hello world"}\n\n'

    # ISO timestamp
    iso = now_iso()
    assert isinstance(iso, str)
    assert "T" in iso

    # JSON-RPC Call Packet
    call_packet = build_jsonrpc_call_packet("add_expense", {"amount": 50, "category": "Food"}, "run_12345678")
    assert call_packet["jsonrpc"] == "2.0"
    assert call_packet["method"] == "tools/call"
    assert call_packet["params"]["name"] == "add_expense"
    assert call_packet["params"]["arguments"]["amount"] == 50

    # JSON-RPC Response Packet
    resp_packet = build_jsonrpc_response_packet("Expense #14 added", "run_12345678")
    assert resp_packet["jsonrpc"] == "2.0"
    assert resp_packet["result"]["content"][0]["text"] == "Expense #14 added"
