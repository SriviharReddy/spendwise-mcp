# System Architecture & Technical Design

SpendWise AI is built on a decoupled, asynchronous architecture connecting a web client, a **FastAPI** orchestrator, a **FastMCP (Model Context Protocol)** tool server, and local **SQLite** storage.

---

![SpendWise Showcase Interface](assets/screenshot.png)


## ⚡ Architecture Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Browser UI (HTML5 / CSS3 / ES Modules)                                  │
│  • Visual Architecture Map & FastMCP Tool Matrix Deck                    │
│  • Live Financial Dashboard (KPI Stats, SVG Donut & Trend Activity)      │
│  • Interactive Agent Chat with Live Tool Execution Cards & Markdown     │
│  • Dynamic Model Selection (/models discovery & Settings dialog)         │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                     HTTP REST APIs  │  Server-Sent Events (SSE)
                    /api/expenses    │  /api/chat/stream
                    /api/budgets     │  (tokens, tool_start, tool_end,
                    /api/models      │   steps, jsonrpc wire frames)
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (backend/main.py)                                       │
│  • Lifespan Context Manager & Static UI Mount (Zero-build deployment)    │
│  • Multi-Provider LLM Factory (DeepSeek, OpenAI, Gemini, Custom)         │
│  • LangGraph Memory Checkpointer (Per-thread conversation continuity)    │
│  • Dynamic Model Discovery (Queries provider /models endpoints)          │
│  • Async SQLite Repository Layer (aiosqlite)                             │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     │ stdio transport (JSON-RPC 2.0)
                                     │ FastMCP protocol
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  FastMCP Server (mcp/mcp-server.py)                                      │
│  • 7 Tools: add_expense, update_expense, delete_expense, list_expenses,  │
│             summarize, set_budget, check_budget                          │
│  • 1 Dynamic Resource: categories://list (Injected into system prompt)   │
│  • SQLite Storage: mcp/expenses.db                                       │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Core Components

### 1. FastMCP Server (`mcp/mcp-server.py`)
- Independent Python process communicating over standard I/O (`stdio`).
- Exposes typed tools with docstrings that define argument schemas for LLM tool binding.
- Serves dynamic resource `categories://list` representing the active taxonomy in `mcp/categories.json`.

### 2. FastAPI Orchestration Engine (`backend/agent.py`)
- Manages connection lifecycle to the FastMCP server using `langchain-mcp-adapters`.
- Dynamically injects the `categories://list` resource into the agent's system prompt along with the current date.
- Uses `langgraph.checkpoint.memory.MemorySaver` for per-session thread persistence across turns.
- Executes the agent with `astream_events` (version 2) and yields Server-Sent Events (SSE) to stream tokens, tool execution starts/ends, and execution durations in real time.

### 3. Dynamic Model Discovery (`backend/routes/api.py`)
- Queries provider `/models` endpoints in real time (`https://api.deepseek.com/models`, `https://api.openai.com/v1/models`, Google Generative AI API) to populate available models without hardcoding.
- Accepts client-supplied API keys from the Settings dialog, persisting them securely in `localStorage`.

### 4. Async Database Layer (`backend/db.py`)
- SQLite storage backed by `aiosqlite`.
- Provides fast aggregations for monthly spending, category breakdown, daily spending trends, and budget health percentages.
