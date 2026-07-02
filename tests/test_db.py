"""Unit tests for the SQLite database repository layer."""

import pytest
from backend.db import (
    create_expense,
    delete_expense,
    get_budgets,
    get_categories,
    get_expense_by_id,
    get_expenses,
    get_summary,
    init_db,
    set_budget,
    update_expense,
)
from backend.seed import seed_database


@pytest.mark.asyncio
async def test_init_db():
    """Verifies that database schema initializes without errors."""
    await init_db()


@pytest.mark.asyncio
async def test_expense_crud_lifecycle():
    """Tests the full lifecycle of an expense: create, read, update, and delete."""
    # 1. Create
    created = await create_expense(
        amount=42.50,
        category="Food",
        subcategory="Dining",
        note="Dinner at Nobu",
        date_str="2026-08-25",
    )
    assert created["id"] is not None
    assert created["amount"] == 42.50
    assert created["category"] == "Food"
    assert created["note"] == "Dinner at Nobu"
    expense_id = created["id"]

    # 2. Read
    fetched = await get_expense_by_id(expense_id)
    assert fetched is not None
    assert fetched["id"] == expense_id
    assert fetched["amount"] == 42.50

    # 3. Query with filter
    items, total = await get_expenses(category="Food", search="Nobu")
    assert total >= 1
    assert any(e["id"] == expense_id for e in items)

    # 4. Update
    updated = await update_expense(
        expense_id=expense_id,
        amount=45.00,
        note="Dinner at Nobu with dessert",
    )
    assert updated is not None
    assert updated["amount"] == 45.00
    assert updated["note"] == "Dinner at Nobu with dessert"

    # 5. Delete
    deleted = await delete_expense(expense_id)
    assert deleted is True

    # 6. Confirm deleted
    post_delete = await get_expense_by_id(expense_id)
    assert post_delete is None


@pytest.mark.asyncio
async def test_budget_operations():
    """Tests setting and querying category budgets."""
    # Set a budget
    res = await set_budget(category="Entertainment", limit_amount=250.00)
    assert res["category"] == "Entertainment"
    assert res["limit_amount"] == 250.00

    # Query budgets
    budgets = await get_budgets()
    assert len(budgets) >= 1
    ent_budget = next((b for b in budgets if b["category"] == "Entertainment"), None)
    assert ent_budget is not None
    assert ent_budget["limit_amount"] == 250.00
    assert "utilization_percentage" in ent_budget


@pytest.mark.asyncio
async def test_summary_and_analytics():
    """Tests summary metrics calculation including category breakdown and trends."""
    # Seed known data
    seed_res = await seed_database()
    assert seed_res["success"] is True

    summary = await get_summary()
    assert summary["total_spent_this_month"] > 0
    assert summary["total_budget_this_month"] > 0
    assert len(summary["category_breakdown"]) > 0
    assert len(summary["daily_trends"]) > 0
    assert summary["top_category"] is not None


def test_categories_taxonomy():
    """Tests category taxonomy reading."""
    cats = get_categories()
    assert "categories" in cats
    assert len(cats["categories"]) >= 10
    assert "Food" in cats["categories"]
