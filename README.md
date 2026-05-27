# SpendWise MCP — Local Expense Tracker (Practice Project)

A practice project designed to explore and learn **LangChain agents**, custom **FastMCP** servers, and **Streamlit** frontends. This repository implements a local AI expense-tracking assistant backed by a local **SQLite** database, communicated over **stdio** via MCP (Model Context Protocol).

## Purpose & Learning Objectives

This repository was created as a practice environment to gain hands-on experience with:
- **Model Context Protocol (MCP)**: Building a custom FastMCP server with SQLite backing, exposing specific CRUD and analytics tools, and a dynamic resource (`categories://list`).
- **LangChain Agents**: Dynamically loading stdio-based MCP tools, instantiating `create_agent` models, and designing comprehensive system prompts.
- **Session State & Memory**: Leveraging LangChain's `MemorySaver` checkpointer in a Streamlit web interface to support per-tab conversation memory.
- **Async Python**: Integrating asynchronous SQLite operations via `aiosqlite` with FastMCP server methods.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Streamlit UI  (app.py)                         │
│  MemorySaver checkpointer — per-session memory  │
└───────────────────┬─────────────────────────────┘
                    │  LangChain create_agent
                    ▼
┌─────────────────────────────────────────────────┐
│  DeepSeek LLM  (deepseek-chat)                  │
└───────────────────┬─────────────────────────────┘
                    │  langchain-mcp-adapters
                    │  stdio transport
                    ▼
┌─────────────────────────────────────────────────┐
│  FastMCP Server  (mcp/mcp-server.py)            │
│  7 tools · 1 resource                          │
│  aiosqlite → mcp/expenses.db                   │
└─────────────────────────────────────────────────┘
```

## Features

| Tool | Description |
|---|---|
| `add_expense` | Record a new expense |
| `update_expense` | Edit an existing expense by ID |
| `delete_expense` | Remove an expense by ID |
| `list_expenses` | Filter and list expenses |
| `summarize` | Group totals by category / subcategory / month |
| `set_budget` | Set a monthly budget limit per category |
| `check_budget` | Show spent vs. limit for any month |

**Resource:** `categories://list` — injected into the agent's system prompt so the LLM always knows valid categories without a tool call.

**Memory:** `MemorySaver` checkpointer with a per-session `thread_id`. Closing/refreshing the browser starts a fresh conversation. The expense data itself persists in SQLite across sessions.

## Setup

### Prerequisites
- Python ≥ 3.13
- [uv](https://docs.astral.sh/uv/) package manager
- A [DeepSeek API key](https://platform.deepseek.com/)

### Install

```bash
git clone https://github.com/your-username/spendwise-mcp.git
cd spendwise-mcp

cp .env.example .env
# Edit .env and fill in DEEPSEEK_API_KEY

uv sync
```

### Run

**Streamlit UI (recommended):**
```bash
uv run streamlit run app.py
```
Open http://localhost:8501.

**Headless smoke-test:**
```bash
uv run python main.py
```

## Project Structure

```
spendwise-mcp/
├── app.py                  # Streamlit chat UI
├── main.py                 # Headless / CLI entrypoint
├── pyproject.toml
├── .env.example
└── mcp/
    ├── mcp-server.py       # FastMCP server (stdio, aiosqlite)
    ├── categories.json     # Valid expense categories
    └── expenses.db         # SQLite database (git-ignored)
```

## Tech Stack

- [LangChain](https://python.langchain.com/) — `create_agent`, `MemorySaver`
- [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) — stdio MCP transport
- [FastMCP](https://gofastmcp.com/) — MCP server framework
- [aiosqlite](https://aiosqlite.omnilib.dev/) — async SQLite
- [DeepSeek](https://platform.deepseek.com/) — `deepseek-chat` LLM
- [Streamlit](https://streamlit.io/) — chat UI
