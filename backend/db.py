"""Async SQLite database repository layer for SpendWise."""

import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Any, AsyncGenerator
import aiosqlite

from backend.config import CATEGORIES_PATH, DB_PATH, logger

# ─── Database Initialization ──────────────────────────────────────────────────


async def init_db() -> None:
    """Creates the SQLite tables if they don't already exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,          -- Format: YYYY-MM-DD
                amount REAL NOT NULL,        -- Monetary expense amount
                category TEXT NOT NULL,      -- General category (e.g. Food, Travel)
                subcategory TEXT,            -- Optional subcategory (e.g. Groceries, Taxi)
                note TEXT                    -- Optional details
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY,   -- The general category
                limit_amount REAL NOT NULL   -- Monthly budget limit
            )
        """)
        await db.commit()
    logger.info("SQLite database schema initialized at %s", DB_PATH)


@asynccontextmanager
async def get_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager for acquiring an aiosqlite database connection."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        yield db


# ─── Expense Operations ───────────────────────────────────────────────────────


async def get_expenses(
    limit: int = 50,
    offset: int = 0,
    category: str | None = None,
    search: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Retrieves filtered and paginated expenses along with total count."""
    query = "SELECT * FROM expenses WHERE 1=1"
    count_query = "SELECT COUNT(*) as total FROM expenses WHERE 1=1"
    params: list[Any] = []

    if category:
        query += " AND category = ?"
        count_query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (note LIKE ? OR subcategory LIKE ? OR category LIKE ?)"
        count_query += " AND (note LIKE ? OR subcategory LIKE ? OR category LIKE ?)"
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern, search_pattern])

    if start_date:
        query += " AND date >= ?"
        count_query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        count_query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date DESC, id DESC LIMIT ? OFFSET ?"
    query_params = list(params) + [limit, offset]

    async with get_connection() as db:
        # Total count
        async with db.execute(count_query, params) as cursor:
            count_row = await cursor.fetchone()
            total = count_row["total"] if count_row else 0

        # Items
        async with db.execute(query, query_params) as cursor:
            rows = await cursor.fetchall()
            expenses = [dict(row) for row in rows]

    return expenses, total


async def get_expense_by_id(expense_id: int) -> dict[str, Any] | None:
    """Fetches a single expense by ID."""
    async with get_connection() as db:
        async with db.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_expense(
    amount: float,
    category: str,
    subcategory: str | None = None,
    note: str | None = None,
    date_str: str | None = None,
) -> dict[str, Any]:
    """Creates a new expense record and returns the created object."""
    if not date_str:
        date_str = date.today().isoformat()

    async with get_connection() as db:
        cursor = await db.execute(
            """
            INSERT INTO expenses (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date_str, amount, category.strip(), subcategory.strip() if subcategory else None, note.strip() if note else None),
        )
        await db.commit()
        expense_id = cursor.lastrowid

    return {
        "id": expense_id,
        "date": date_str,
        "amount": amount,
        "category": category.strip(),
        "subcategory": subcategory.strip() if subcategory else None,
        "note": note.strip() if note else None,
    }


async def update_expense(
    expense_id: int,
    amount: float | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    note: str | None = None,
    date_str: str | None = None,
) -> dict[str, Any] | None:
    """Updates an existing expense and returns the updated record."""
    current = await get_expense_by_id(expense_id)
    if not current:
        return None

    new_amount = amount if amount is not None else current["amount"]
    new_category = category.strip() if category is not None else current["category"]
    new_subcat = subcategory.strip() if subcategory is not None else current["subcategory"]
    new_note = note.strip() if note is not None else current["note"]
    new_date = date_str if date_str is not None else current["date"]

    async with get_connection() as db:
        await db.execute(
            """
            UPDATE expenses
            SET amount = ?, category = ?, subcategory = ?, note = ?, date = ?
            WHERE id = ?
            """,
            (new_amount, new_category, new_subcat, new_note, new_date, expense_id),
        )
        await db.commit()

    return {
        "id": expense_id,
        "date": new_date,
        "amount": new_amount,
        "category": new_category,
        "subcategory": new_subcat,
        "note": new_note,
    }


async def delete_expense(expense_id: int) -> bool:
    """Deletes an expense record by ID."""
    async with get_connection() as db:
        cursor = await db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        await db.commit()
        return cursor.rowcount > 0


# ─── Budget Operations ────────────────────────────────────────────────────────


async def get_budgets(month: str | None = None) -> list[dict[str, Any]]:
    """Retrieves all category budgets with spent amounts for the given month (default current month)."""
    if not month:
        month = date.today().strftime("%Y-%m")

    async with get_connection() as db:
        # Get all budgets
        async with db.execute("SELECT category, limit_amount FROM budgets ORDER BY category ASC") as cursor:
            budget_rows = await cursor.fetchall()

        # Get spending per category for this month
        async with db.execute(
            """
            SELECT category, SUM(amount) as spent
            FROM expenses
            WHERE strftime('%Y-%m', date) = ?
            GROUP BY category
            """,
            (month,),
        ) as cursor:
            spend_rows = await cursor.fetchall()

    spending_map = {row["category"]: row["spent"] for row in spend_rows}

    results = []
    for b in budget_rows:
        cat = b["category"]
        limit = b["limit_amount"]
        spent = spending_map.get(cat, 0.0)
        util_pct = round((spent / limit * 100.0), 1) if limit > 0 else 0.0
        results.append({
            "category": cat,
            "limit_amount": limit,
            "spent_this_month": round(spent, 2),
            "utilization_percentage": util_pct,
            "is_over_budget": spent > limit,
        })

    return results


async def set_budget(category: str, limit_amount: float) -> dict[str, Any]:
    """Sets or updates a monthly budget limit for a category."""
    cat_clean = category.strip()
    async with get_connection() as db:
        await db.execute(
            """
            INSERT INTO budgets (category, limit_amount)
            VALUES (?, ?)
            ON CONFLICT(category) DO UPDATE SET limit_amount = excluded.limit_amount
            """,
            (cat_clean, limit_amount),
        )
        await db.commit()

    return {"category": cat_clean, "limit_amount": limit_amount}


# ─── Summary & Analytics Operations ──────────────────────────────────────────


async def get_summary(month: str | None = None) -> dict[str, Any]:
    """Computes comprehensive dashboard metrics for the given month."""
    if not month:
        month = date.today().strftime("%Y-%m")

    # Compute previous month for MoM comparison
    try:
        current_dt = datetime.strptime(month, "%Y-%m")
        if current_dt.month == 1:
            prev_month = f"{current_dt.year - 1}-12"
        else:
            prev_month = f"{current_dt.year}-{current_dt.month - 1:02d}"
    except Exception:
        prev_month = ""

    async with get_connection() as db:
        # Total spent and transactions this month
        async with db.execute(
            """
            SELECT SUM(amount) as total_spent, COUNT(*) as tx_count
            FROM expenses
            WHERE strftime('%Y-%m', date) = ?
            """,
            (month,),
        ) as cursor:
            summary_row = await cursor.fetchone()
            total_spent = summary_row["total_spent"] or 0.0
            tx_count = summary_row["tx_count"] or 0

        # Total spent in previous month
        prev_spent = 0.0
        if prev_month:
            async with db.execute(
                """
                SELECT SUM(amount) as total_spent
                FROM expenses
                WHERE strftime('%Y-%m', date) = ?
                """,
                (prev_month,),
            ) as cursor:
                prev_row = await cursor.fetchone()
                if prev_row and prev_row["total_spent"]:
                    prev_spent = prev_row["total_spent"]

        # Category breakdown
        async with db.execute(
            """
            SELECT category, SUM(amount) as cat_amount, COUNT(*) as cat_count
            FROM expenses
            WHERE strftime('%Y-%m', date) = ?
            GROUP BY category
            ORDER BY cat_amount DESC
            """,
            (month,),
        ) as cursor:
            cat_rows = await cursor.fetchall()

        # Daily trends
        async with db.execute(
            """
            SELECT date, SUM(amount) as daily_amount
            FROM expenses
            WHERE strftime('%Y-%m', date) = ?
            GROUP BY date
            ORDER BY date ASC
            """,
            (month,),
        ) as cursor:
            daily_rows = await cursor.fetchall()

        # Total monthly budget
        async with db.execute("SELECT SUM(limit_amount) as total_budget FROM budgets") as cursor:
            b_row = await cursor.fetchone()
            total_budget = b_row["total_budget"] or 0.0

    # Process category breakdown
    category_breakdown = []
    top_cat = None
    top_cat_amount = 0.0

    for idx, row in enumerate(cat_rows):
        amt = row["cat_amount"]
        pct = round((amt / total_spent * 100.0), 1) if total_spent > 0 else 0.0
        category_breakdown.append({
            "category": row["category"],
            "amount": round(amt, 2),
            "percentage": pct,
            "transaction_count": row["cat_count"],
        })
        if idx == 0:
            top_cat = row["category"]
            top_cat_amount = round(amt, 2)

    # Process daily trends
    daily_trends = [
        {"date": row["date"], "amount": round(row["daily_amount"], 2)}
        for row in daily_rows
    ]

    # Month over month change
    mom_change_pct = None
    if prev_spent > 0:
        mom_change_pct = round(((total_spent - prev_spent) / prev_spent * 100.0), 1)

    budget_util_pct = round((total_spent / total_budget * 100.0), 1) if total_budget > 0 else 0.0

    return {
        "month": month,
        "total_spent_this_month": round(total_spent, 2),
        "total_budget_this_month": round(total_budget, 2),
        "budget_utilization_pct": budget_util_pct,
        "top_category": top_cat,
        "top_category_amount": top_cat_amount,
        "total_transactions_this_month": tx_count,
        "category_breakdown": category_breakdown,
        "daily_trends": daily_trends,
        "previous_month_spent": round(prev_spent, 2),
        "mom_change_pct": mom_change_pct,
    }


# ─── Category Taxonomy ────────────────────────────────────────────────────────


def get_categories() -> dict[str, Any]:
    """Reads categories taxonomy from categories.json."""
    if CATEGORIES_PATH.exists():
        try:
            with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to read categories.json: %s", e)
    return {
        "categories": [
            "Food", "Travel", "Transportation", "Utilities", "Entertainment",
            "Housing", "Shopping", "Health", "Education", "Personal Care",
            "Finance", "Gifts", "Family", "Pets", "Work", "Miscellaneous",
        ]
    }
