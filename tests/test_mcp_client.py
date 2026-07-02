"""Integration tests for FastMCP client manager and schema reflection."""

import pytest
from backend.mcp_client import mcp_manager


@pytest.mark.asyncio
async def test_mcp_metadata_reflection():
    """Tests that FastMCP stdio server reflects all 7 tools and 1 resource."""
    meta = await mcp_manager.get_metadata()

    assert meta.server_name == "Expense Tracker (FastMCP)"
    assert meta.transport == "stdio"
    assert meta.status == "connected"
    assert len(meta.tools) == 7

    tool_names = [t.name for t in meta.tools]
    assert "add_expense" in tool_names
    assert "update_expense" in tool_names
    assert "delete_expense" in tool_names
    assert "list_expenses" in tool_names
    assert "summarize" in tool_names
    assert "set_budget" in tool_names
    assert "check_budget" in tool_names

    # Check categories resource
    assert len(meta.resources) >= 1
    assert any(r.uri == "categories://list" for r in meta.resources)


@pytest.mark.asyncio
async def test_categories_resource_read():
    """Tests reading the dynamic categories://list resource over FastMCP session."""
    categories_text = await mcp_manager.get_categories_resource()
    assert "categories" in categories_text
    assert "Food" in categories_text
