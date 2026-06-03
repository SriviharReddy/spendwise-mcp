"""Pydantic v2 domain schemas for SpendWise API contracts and telemetry."""

from typing import Any
from pydantic import BaseModel, Field


# ─── Expense Models ──────────────────────────────────────────────────────────


class ExpenseBase(BaseModel):
    """Base schema for an expense record."""

    amount: float = Field(..., gt=0, description="Expense monetary amount (> 0)")
    category: str = Field(..., min_length=1, description="General category (e.g. Food)")
    subcategory: str | None = Field(default=None, description="Optional subcategory (e.g. Groceries)")
    note: str | None = Field(default=None, description="Optional description or note")
    date: str | None = Field(default=None, description="Date in YYYY-MM-DD format (defaults to today)")


class ExpenseCreate(ExpenseBase):
    """Schema for creating a new expense."""

    pass


class ExpenseUpdate(BaseModel):
    """Schema for updating an existing expense (all fields optional)."""

    amount: float | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, min_length=1)
    subcategory: str | None = None
    note: str | None = None
    date: str | None = None


class ExpenseResponse(BaseModel):
    """Schema representing an expense returned by the API."""

    id: int
    date: str
    amount: float
    category: str
    subcategory: str | None = None
    note: str | None = None


class ExpenseListResponse(BaseModel):
    """Paginated list of expenses."""

    expenses: list[ExpenseResponse]
    total: int
    limit: int
    offset: int


# ─── Budget Models ───────────────────────────────────────────────────────────


class BudgetBase(BaseModel):
    """Base schema for a category monthly budget."""

    category: str = Field(..., min_length=1, description="Category name")
    limit_amount: float = Field(..., gt=0, description="Monthly spending limit")


class BudgetCreate(BudgetBase):
    """Schema for creating or updating a budget."""

    pass


class BudgetResponse(BaseModel):
    """Schema representing a category budget with current month utilization."""

    category: str
    limit_amount: float
    spent_this_month: float = 0.0
    utilization_percentage: float = 0.0
    is_over_budget: bool = False


class BudgetListResponse(BaseModel):
    """List of all category budgets."""

    budgets: list[BudgetResponse]
    total_budget_limit: float = 0.0
    total_budget_spent: float = 0.0


# ─── Analytics & Summary Models ──────────────────────────────────────────────


class CategoryBreakdownItem(BaseModel):
    """Category spending breakdown item."""

    category: str
    amount: float
    percentage: float
    transaction_count: int


class DailySpendingItem(BaseModel):
    """Daily spending trend item."""

    date: str
    amount: float


class SummaryResponse(BaseModel):
    """Dashboard top-level summary metrics."""

    month: str  # YYYY-MM
    total_spent_this_month: float
    total_budget_this_month: float
    budget_utilization_pct: float
    top_category: str | None
    top_category_amount: float
    total_transactions_this_month: int
    category_breakdown: list[CategoryBreakdownItem]
    daily_trends: list[DailySpendingItem]
    previous_month_spent: float
    mom_change_pct: float | None = None


# ─── Dynamic Models & Provider Reflection Models ─────────────────────────────


class ModelsRequest(BaseModel):
    """Request payload for fetching dynamic models from provider's /models endpoint."""

    provider: str = Field(..., description="Target provider (deepseek, openai, gemini, custom)")
    api_key: str | None = Field(default=None, description="Optional client-supplied API key")
    base_url: str | None = Field(default=None, description="Optional custom base URL for OpenAI-compatible/Ollama")


class ModelItem(BaseModel):
    """Schema representing a single LLM model from the /models endpoint."""

    id: str
    name: str
    description: str | None = None


class ModelsResponse(BaseModel):
    """Response payload containing available models for a provider."""

    provider: str
    models: list[ModelItem]
    default_model: str | None = None


# ─── Chat & Agent Telemetry Models ───────────────────────────────────────────


class ChatStreamRequest(BaseModel):
    """Request payload for the agent chat stream."""

    message: str = Field(..., min_length=1, description="User prompt or query")
    thread_id: str | None = Field(default=None, description="Conversation session ID for memory")
    provider: str | None = Field(default=None, description="Target LLM provider override")
    model: str | None = Field(default=None, description="Target model identifier override")
    api_key: str | None = Field(default=None, description="Optional user-provided API key")
    base_url: str | None = Field(default=None, description="Optional custom base URL")


class AgentTelemetryEvent(BaseModel):
    """Event packet emitted over Server-Sent Events."""

    event: str  # lifecycle_start, pipeline_step, tool_start, tool_end, token, done, error
    step: str | None = None  # prompt_context, llm_reasoning, mcp_dispatch, synthesis
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: str | None = None


# ─── MCP Reflection Models ───────────────────────────────────────────────────


class MCPToolParameter(BaseModel):
    """Parameter definition for an MCP tool."""

    name: str
    type: str
    description: str | None = None
    required: bool = False


class MCPToolInfo(BaseModel):
    """Metadata describing an active FastMCP tool."""

    name: str
    description: str
    parameters: list[MCPToolParameter] = Field(default_factory=list)


class MCPResourceInfo(BaseModel):
    """Metadata describing an active FastMCP resource."""

    uri: str
    name: str
    description: str | None = None
    mime_type: str = "application/json"


class MCPMetadataResponse(BaseModel):
    """Overview of connected FastMCP server tools and resources."""

    server_name: str
    transport: str
    status: str
    tools: list[MCPToolInfo]
    resources: list[MCPResourceInfo]


# ─── System Health Models ────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """Application health and configuration status."""

    status: str
    version: str = "1.0.0"
    mcp_server: str
    tools_count: int
    active_provider: str
    available_providers: list[dict[str, Any]]
