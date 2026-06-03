"""REST API endpoints for SpendWise dashboard, CRUD, seed, MCP inspection, and dynamic model fetching."""

from typing import Any
import httpx
from fastapi import APIRouter, HTTPException, Query

from backend.config import get_available_providers, logger, settings
from backend.db import (
    create_expense,
    delete_expense,
    get_budgets,
    get_categories,
    get_expense_by_id,
    get_expenses,
    get_summary,
    set_budget,
    update_expense,
)
from backend.mcp_client import mcp_manager
from backend.models import (
    BudgetCreate,
    BudgetListResponse,
    BudgetResponse,
    ExpenseCreate,
    ExpenseListResponse,
    ExpenseResponse,
    ExpenseUpdate,
    HealthResponse,
    MCPMetadataResponse,
    ModelItem,
    ModelsRequest,
    ModelsResponse,
    SummaryResponse,
)
from backend.seed import seed_database

router = APIRouter(prefix="/api", tags=["Financial & MCP API"])


# ─── Dynamic Model Reflection from Provider Endpoints ─────────────────────────


@router.post("/models", response_model=ModelsResponse)
async def get_provider_models(payload: ModelsRequest) -> ModelsResponse:
    """Queries the provider's real /models endpoint to retrieve available models."""
    provider = payload.provider.lower().strip()
    models_list: list[ModelItem] = []
    default_model = None

    try:
        if provider == "deepseek":
            api_key = (payload.api_key or settings.deepseek_api_key).strip()
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail="DeepSeek API Key is missing. Please configure it in Settings.",
                )

            base_url = (payload.base_url or "https://api.deepseek.com").rstrip("/")
            url = f"{base_url}/models"

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"DeepSeek returned {resp.status_code}: {resp.text}",
                    )
                data = resp.json()
                raw_models = data.get("data", [])
                for item in raw_models:
                    m_id = item.get("id", "")
                    name = "DeepSeek Chat (V3)" if m_id == "deepseek-chat" else "DeepSeek Reasoner (R1)" if m_id == "deepseek-reasoner" else m_id
                    models_list.append(ModelItem(id=m_id, name=name, description="DeepSeek Model"))
                default_model = "deepseek-chat"

        elif provider == "openai":
            api_key = (payload.api_key or settings.openai_api_key).strip()
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail="OpenAI API Key is missing. Please configure it in Settings.",
                )

            base_url = (payload.base_url or "https://api.openai.com/v1").rstrip("/")
            url = f"{base_url}/models"

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"OpenAI returned {resp.status_code}: {resp.text}",
                    )
                data = resp.json()
                raw_models = data.get("data", [])

                # Filter and rank chat-capable models
                preferred_order = ["gpt-4o", "gpt-4o-mini", "o3-mini", "o1", "o1-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
                seen = set()

                for pref in preferred_order:
                    for m in raw_models:
                        m_id = m.get("id", "")
                        if m_id == pref and m_id not in seen:
                            seen.add(m_id)
                            models_list.append(ModelItem(id=m_id, name=m_id, description="OpenAI Chat Model"))

                # Append any other gpt / o-series models
                for m in raw_models:
                    m_id = m.get("id", "")
                    if (m_id.startswith("gpt-") or m_id.startswith("o1") or m_id.startswith("o3") or m_id.startswith("chatgpt")) and m_id not in seen:
                        seen.add(m_id)
                        models_list.append(ModelItem(id=m_id, name=m_id, description="OpenAI Model"))

                default_model = "gpt-4o-mini" if "gpt-4o-mini" in seen else (models_list[0].id if models_list else "gpt-4o")

        elif provider in ("gemini", "google"):
            api_key = (payload.api_key or settings.google_api_key).strip()
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail="Google Gemini API Key is missing. Please configure it in Settings.",
                )

            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"Google Gemini returned {resp.status_code}: {resp.text}",
                    )
                data = resp.json()
                raw_models = data.get("models", [])

                for m in raw_models:
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        raw_name = m.get("name", "")
                        clean_id = raw_name.replace("models/", "")
                        display_name = m.get("displayName", clean_id)
                        models_list.append(ModelItem(id=clean_id, name=display_name, description=m.get("description")))

                default_model = "gemini-2.0-flash" if any(m.id == "gemini-2.0-flash" for m in models_list) else (models_list[0].id if models_list else "gemini-1.5-flash")

        elif provider in ("custom", "openrouter"):
            base_url = (payload.base_url or "https://openrouter.ai/api/v1").rstrip("/")
            api_key = (payload.api_key or settings.openai_api_key).strip()
            url = f"{base_url}/models"

            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"Custom endpoint returned {resp.status_code}: {resp.text}",
                    )
                data = resp.json()
                raw_models = data.get("data", []) or data.get("models", [])
                for m in raw_models[:50]:  # Limit to 50 for readability
                    m_id = m.get("id") or m.get("name", "")
                    m_name = m.get("name") or m_id
                    models_list.append(ModelItem(id=m_id, name=m_name, description=m.get("description")))

                default_model = models_list[0].id if models_list else "default"

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to query /models endpoint for provider %s: %s", provider, e)
        raise HTTPException(status_code=502, detail=f"Failed to fetch models from {provider}: {str(e)}")

    if not models_list:
        raise HTTPException(status_code=404, detail=f"No chat models returned by {provider}.")

    return ModelsResponse(
        provider=provider,
        models=models_list,
        default_model=default_model,
    )


# ─── System & MCP Inspection ──────────────────────────────────────────────────


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Returns application status, LLM configuration, and MCP server health."""
    mcp_meta = await mcp_manager.get_metadata()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        mcp_server=mcp_meta.status,
        tools_count=len(mcp_meta.tools),
        active_provider=settings.default_provider,
        available_providers=get_available_providers(),
    )


@router.get("/mcp/metadata", response_model=MCPMetadataResponse)
async def get_mcp_metadata() -> MCPMetadataResponse:
    """Introspects and returns active FastMCP tools, schemas, and resources."""
    return await mcp_manager.get_metadata()


@router.get("/categories")
async def get_categories_endpoint() -> dict[str, Any]:
    """Returns standard expense categories taxonomy."""
    return get_categories()


# ─── Expenses CRUD ────────────────────────────────────────────────────────────


@router.get("/expenses", response_model=ExpenseListResponse)
async def list_expenses(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    category: str | None = None,
    search: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> ExpenseListResponse:
    """Returns a filtered, paginated list of expense records."""
    expenses, total = await get_expenses(
        limit=limit,
        offset=offset,
        category=category,
        search=search,
        start_date=start_date,
        end_date=end_date,
    )
    items = [ExpenseResponse(**e) for e in expenses]
    return ExpenseListResponse(
        expenses=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/expenses", response_model=ExpenseResponse, status_code=201)
async def create_expense_endpoint(payload: ExpenseCreate) -> ExpenseResponse:
    """Records a new expense in the database."""
    created = await create_expense(
        amount=payload.amount,
        category=payload.category,
        subcategory=payload.subcategory,
        note=payload.note,
        date_str=payload.date,
    )
    return ExpenseResponse(**created)


@router.get("/expenses/{expense_id}", response_model=ExpenseResponse)
async def get_expense_endpoint(expense_id: int) -> ExpenseResponse:
    """Fetches a single expense record by ID."""
    expense = await get_expense_by_id(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail=f"Expense with ID {expense_id} not found.")
    return ExpenseResponse(**expense)


@router.put("/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense_endpoint(expense_id: int, payload: ExpenseUpdate) -> ExpenseResponse:
    """Updates an existing expense record."""
    updated = await update_expense(
        expense_id=expense_id,
        amount=payload.amount,
        category=payload.category,
        subcategory=payload.subcategory,
        note=payload.note,
        date_str=payload.date,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Expense with ID {expense_id} not found.")
    return ExpenseResponse(**updated)


# ─── Clear Database ───────────────────────────────────────────────────────────


@router.post("/clear")
async def clear_database_endpoint() -> dict[str, Any]:
    """Clears all expenses and budgets so the user starts with a clean slate."""
    import aiosqlite
    from backend.config import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM expenses")
        await db.execute("DELETE FROM budgets")
        await db.commit()
    return {"success": True, "message": "All expense and budget records cleared."}


@router.delete("/expenses/{expense_id}")
async def delete_expense_endpoint(expense_id: int) -> dict[str, bool]:
    """Deletes an expense record by ID."""
    deleted = await delete_expense(expense_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Expense with ID {expense_id} not found.")
    return {"success": True}


# ─── Budgets ──────────────────────────────────────────────────────────────────


@router.get("/budgets", response_model=BudgetListResponse)
async def list_budgets(month: str | None = None) -> BudgetListResponse:
    """Returns all category budgets and their utilization for the given month."""
    budgets_data = await get_budgets(month=month)
    items = [BudgetResponse(**b) for b in budgets_data]
    total_limit = sum(b.limit_amount for b in items)
    total_spent = sum(b.spent_this_month for b in items)
    return BudgetListResponse(
        budgets=items,
        total_budget_limit=round(total_limit, 2),
        total_budget_spent=round(total_spent, 2),
    )


@router.post("/budgets", response_model=BudgetResponse)
async def set_budget_endpoint(payload: BudgetCreate) -> BudgetResponse:
    """Sets or updates a monthly budget limit for a category."""
    await set_budget(category=payload.category, limit_amount=payload.limit_amount)
    budgets = await get_budgets()
    for b in budgets:
        if b["category"] == payload.category.strip():
            return BudgetResponse(**b)
    return BudgetResponse(
        category=payload.category.strip(),
        limit_amount=payload.limit_amount,
    )


# ─── Summary & Metrics ────────────────────────────────────────────────────────


@router.get("/summary", response_model=SummaryResponse)
async def get_summary_endpoint(month: str | None = None) -> SummaryResponse:
    """Returns calculated KPIs, category breakdown, and daily trend series."""
    data = await get_summary(month=month)
    return SummaryResponse(**data)


# ─── Seed Trigger ─────────────────────────────────────────────────────────────


@router.post("/seed")
async def seed_data_endpoint() -> dict[str, Any]:
    """Resets and populates the database with realistic demonstration data."""
    return await seed_database()
