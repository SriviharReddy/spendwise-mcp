import os
import sys
import asyncio
import uuid
from datetime import date

import streamlit as st
from dotenv import load_dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp", "mcp-server.py")


def run_sync(coro):
    """Always run an async coroutine on a fresh event loop (safe for Streamlit)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _fetch_categories() -> str:
    client = MultiServerMCPClient({
        "expense_tracker": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [SERVER_PATH],
        }
    })
    async with client.session("expense_tracker") as session:
        result = await session.read_resource("categories://list")
        return result.contents[0].text if result.contents else "{}"


async def _invoke_agent(
    user_input: str,
    checkpointer: MemorySaver,
    thread_id: str,
    system_prompt: str,
) -> str:
    llm = ChatDeepSeek(
        model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        extra_body={"thinking": {"type": "disabled"}},
    )
    client = MultiServerMCPClient({
        "expense_tracker": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [SERVER_PATH],
        }
    })
    async with client.session("expense_tracker") as session:
        tools = await load_mcp_tools(session)

        # The same checkpointer + thread_id restores full conversation history
        # even though we create a fresh agent object each call.
        agent = create_agent(
            model=llm,
            tools=tools,
            checkpointer=checkpointer,
            system_prompt=system_prompt,
        )
        response = await agent.ainvoke(
            {"messages": user_input},
            config={"configurable": {"thread_id": thread_id}},
        )

    last_msg = response["messages"][-1]
    return last_msg.content if hasattr(last_msg, "content") else str(last_msg)


def init_session():
    """Called once per browser session. Wires up checkpointer + thread ID."""
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.checkpointer = MemorySaver()
        st.session_state.messages = []  # for display only

        categories_json = run_sync(_fetch_categories())
        st.session_state.system_prompt = (
            "You are a helpful expense tracking assistant. "
            "Use the available tools to manage expenses, budgets, and summaries.\n\n"
            f"Today is {date.today().isoformat()}.\n\n"
            f"Valid categories:\n{categories_json}"
        )


def main():
    st.title("Expense Tracker")

    init_session()

    # Replay chat history on every rerun
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("Ask about your expenses…"):
        # Show user bubble immediately
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Stream the agent response
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    reply = run_sync(_invoke_agent(
                        user_input,
                        st.session_state.checkpointer,
                        st.session_state.thread_id,
                        st.session_state.system_prompt,
                    ))
                except Exception as e:
                    reply = f"⚠️ Error: {e}"
            st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
