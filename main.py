"""
main.py — headless smoke-test / programmatic entry point.

Run via:
    uv run python main.py

The main UI is app.py (Streamlit). This file is useful for
quick one-off queries or automated testing without launching
the browser.
"""

import os
import sys
import asyncio
from datetime import date
from dotenv import load_dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek

load_dotenv()

SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp", "mcp-server.py")


async def run_query(query: str) -> str:
    """Send a single query to the expense-tracker agent and return the reply."""
    llm = ChatDeepSeek(
        model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        extra_body={"thinking": {"type": "disabled"}},
    )

    client = MultiServerMCPClient(
        {
            "expense_tracker": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [SERVER_PATH],
            }
        }
    )

    async with client.session("expense_tracker") as session:
        tools = await load_mcp_tools(session)

        resource_result = await session.read_resource("categories://list")
        categories_json = (
            resource_result.contents[0].text if resource_result.contents else "{}"
        )

        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=(
                "You are a helpful expense tracking assistant. "
                "Use the available tools to manage expenses, budgets, and summaries.\n\n"
                f"Today is {date.today().isoformat()}.\n\n"
                f"Valid categories:\n{categories_json}"
            ),
        )

        response = await agent.ainvoke({"messages": query})

    last_msg = response["messages"][-1]
    return last_msg.content if hasattr(last_msg, "content") else str(last_msg)


if __name__ == "__main__":
    query = "List my recorded expenses."
    result = asyncio.run(run_query(query))
    print(result)
