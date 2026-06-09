"""FastMCP client wrapper, stdio transport manager, and schema reflection."""

import sys
from typing import Any
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from backend.config import MCP_SERVER_PATH, logger
from backend.models import (
    MCPMetadataResponse,
    MCPResourceInfo,
    MCPToolInfo,
    MCPToolParameter,
)

SERVER_KEY = "expense_tracker"


class MCPClientManager:
    """Manages the FastMCP stdio client and tool/resource reflection."""

    def __init__(self) -> None:
        self._server_path = str(MCP_SERVER_PATH.resolve())
        self._client: MultiServerMCPClient | None = None

    def _ensure_client(self) -> MultiServerMCPClient:
        """Initializes the MultiServerMCPClient if not already created."""
        if self._client is None:
            logger.info("Initializing MultiServerMCPClient with stdio transport: %s", self._server_path)
            self._client = MultiServerMCPClient({
                SERVER_KEY: {
                    "transport": "stdio",
                    "command": sys.executable,
                    "args": [self._server_path],
                }
            })
        return self._client

    def session(self):
        """Async context manager yielding an MCP session."""
        client = self._ensure_client()
        return client.session(SERVER_KEY)

    async def get_tools(self, session=None) -> list[Any]:
        """Loads and returns all MCP tools from the FastMCP server."""
        if session is not None:
            return await load_mcp_tools(session)
        async with self.session() as sess:
            return await load_mcp_tools(sess)

    async def get_categories_resource(self, session=None) -> str:
        """Reads the standard categories resource from FastMCP (categories://list)."""
        try:
            if session is not None:
                result = await session.read_resource("categories://list")
            else:
                async with self.session() as sess:
                    result = await sess.read_resource("categories://list")

            if result and result.contents and len(result.contents) > 0:
                return result.contents[0].text
        except Exception as e:
            logger.warning("Could not read categories://list from MCP server: %s", e)
        return '{"categories": ["Food", "Transportation", "Housing", "Utilities", "Entertainment", "Shopping"]}'

    async def get_metadata(self) -> MCPMetadataResponse:
        """Introspects and returns metadata for all active FastMCP tools and resources."""
        tools_info: list[MCPToolInfo] = []
        resources_info: list[MCPResourceInfo] = [
            MCPResourceInfo(
                uri="categories://list",
                name="Category Taxonomy",
                description="List of valid general expense categories and subcategories",
                mime_type="application/json",
            )
        ]

        try:
            async with self.session() as sess:
                tools = await load_mcp_tools(sess)
                for tool in tools:
                    params: list[MCPToolParameter] = []
                    args_schema = getattr(tool, "args", {}) or {}
                    if isinstance(args_schema, dict):
                        for p_name, p_details in args_schema.items():
                            if isinstance(p_details, dict):
                                params.append(
                                    MCPToolParameter(
                                        name=p_name,
                                        type=str(p_details.get("type", "string")),
                                        description=p_details.get("description", p_details.get("title")),
                                        required=bool(p_details.get("required", False)),
                                    )
                                )
                            else:
                                params.append(
                                    MCPToolParameter(
                                        name=p_name,
                                        type="string",
                                        description=None,
                                        required=False,
                                    )
                                )

                    tools_info.append(
                        MCPToolInfo(
                            name=tool.name,
                            description=tool.description or "No description provided.",
                            parameters=params,
                        )
                    )

            status = "connected"
        except Exception as e:
            logger.error("Failed to introspect MCP metadata: %s", e)
            status = f"error: {e}"

        return MCPMetadataResponse(
            server_name="Expense Tracker (FastMCP)",
            transport="stdio",
            status=status,
            tools=tools_info,
            resources=resources_info,
        )


# Global singleton instance
mcp_manager = MCPClientManager()
