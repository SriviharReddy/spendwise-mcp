# REST API & SSE Protocol Reference

FastAPI backend endpoints and Server-Sent Events (SSE) streaming specifications.

---

## 📡 REST Endpoints

### System & Models
- `GET /api/health`: Health status, active provider, connected FastMCP server status.
- `GET /api/mcp/metadata`: Introspects FastMCP tools, schemas, and resource definitions.
- `POST /api/models`: Queries provider `/models` endpoints (`deepseek`, `openai`, `gemini`, `custom`) and returns available models.
  - **Body**: `{ "provider": "deepseek", "api_key": "...", "base_url": "..." }`
- `GET /api/categories`: Returns valid categories taxonomy.

### Financial Data
- `GET /api/summary?month=YYYY-MM`: Dashboard KPIs, category breakdowns, daily trends, and MoM delta.
- `GET /api/budgets?month=YYYY-MM`: Category budget limits, spent amounts, and utilization percentages.
- `POST /api/budgets`: Create or update a category budget.
  - **Body**: `{ "category": "Food", "limit_amount": 600.0 }`
- `GET /api/expenses?limit=50&offset=0&category=...&search=...`: Paginated and filtered expense records.
- `POST /api/expenses`: Record an expense directly.
  - **Body**: `{ "amount": 42.50, "category": "Food", "subcategory": "Dining", "note": "Dinner" }`
- `PUT /api/expenses/{id}`: Update an existing expense.
- `DELETE /api/expenses/{id}`: Delete an expense by ID.
- `POST /api/seed`: Populate sample demonstration dataset (~35 transactions and 6 budgets).
- `POST /api/clear`: Wipe all expense and budget records for a clean slate.

---

## ⚡ Real-Time Chat Stream (`POST /api/chat/stream`)

Streams agent execution events over Server-Sent Events (`text/event-stream`).

### Request Payload
```json
{
  "message": "Log $42.50 dinner at Nobu today under Food",
  "thread_id": "session-xyz",
  "provider": "deepseek",
  "model": "deepseek-chat",
  "api_key": "sk-...",
  "base_url": "https://api.deepseek.com"
}
```

### Emitted Events

| Event | Description | Payload Data |
|---|---|---|
| `lifecycle_start` | Session initiated | `{ "thread_id": "...", "provider": "...", "model": "..." }` |
| `pipeline_step` | Step transition | `{ "step": "prompt_context" \| "llm_reasoning" \| "synthesis" }` |
| `tool_start` | Tool invoked | `{ "tool": "add_expense", "input": {...}, "jsonrpc": {...} }` |
| `tool_end` | Tool finished | `{ "tool": "add_expense", "output": "...", "duration_ms": 14 }` |
| `token` | Streamed text chunk | `{ "delta": "I've logged your..." }` |
| `done` | Stream completed | `{ "thread_id": "...", "total_duration_ms": 1120 }` |
| `error` | Failure event | `{ "error": "Detailed error message" }` |
