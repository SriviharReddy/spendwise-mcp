# /// script
# dependencies = [
#     "fastmcp>=3.3.1",
#     "aiosqlite>=0.20.0",
# ]
# ///

import os
import asyncio
import sqlite3
import contextlib
import aiosqlite
from datetime import datetime
from typing import Optional
from fastmcp import FastMCP

# Initialize the FastMCP server
mcp = FastMCP("Expense Tracker")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "expenses.db")

# ─── DB Initialization ────────────────────────────────────────────────────────

_db_initialized = False
_db_lock: asyncio.Lock | None = None


async def ensure_db_initialized():
    """Ensures that the database schema is initialized exactly once."""
    global _db_initialized, _db_lock
    if _db_initialized:
        return
    if _db_lock is None:
        _db_lock = asyncio.Lock()
    async with _db_lock:
        if not _db_initialized:
            await init_db()
            _db_initialized = True


async def init_db():
    """Creates the SQLite tables if they don't already exist."""
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


@contextlib.asynccontextmanager
async def get_db():
    """Async context manager for acquiring a local aiosqlite connection."""
    await ensure_db_initialized()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        yield db


# ─── Resource ─────────────────────────────────────────────────────────────────

@mcp.resource("categories://list")
async def get_categories() -> str:
    """Get the standard list of expense categories and subcategories in JSON format."""
    categories_path = os.path.join(BASE_DIR, "categories.json")
    try:
        with open(categories_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f'{{"error": "Failed to read categories: {str(e)}"}}'


# ─── Tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def add_expense(
    amount: float,
    category: str,
    subcategory: Optional[str] = None,
    note: Optional[str] = None,
    date: Optional[str] = None,
) -> str:
    """Add a new expense to the database.

    Args:
        amount: The monetary value of the expense (must be greater than zero).
        category: General category (e.g., Food, Travel, Utilities).
        subcategory: Optional specific subcategory (e.g., Groceries, Taxi).
        note: Optional description or details.
        date: Optional date in YYYY-MM-DD format. Defaults to today's date.
    """
    if amount <= 0:
        return "Error: Amount must be greater than zero."

    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return "Error: Date must be in YYYY-MM-DD format."
    else:
        date = datetime.now().strftime("%Y-%m-%d")

    category = category.strip()
    if not category:
        return "Error: Category cannot be empty."

    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO expenses (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date, amount, category, subcategory, note),
        )
        await db.commit()
        expense_id = cursor.lastrowid

    subcat_str = f", Subcategory: {subcategory}" if subcategory else ""
    note_str = f", Note: {note}" if note else ""
    return (
        f"Success: Expense added with ID {expense_id} "
        f"(Date: {date}, Amount: {amount:.2f}, Category: {category}{subcat_str}{note_str})"
    )


@mcp.tool()
async def update_expense(
    expense_id: int,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    note: Optional[str] = None,
    date: Optional[str] = None,
) -> str:
    """Update an existing expense in the database.

    Args:
        expense_id: The ID of the expense to update.
        amount: Optional new monetary value (must be greater than zero).
        category: Optional new general category.
        subcategory: Optional new subcategory (pass empty string "" to clear).
        note: Optional new description (pass empty string "" to clear).
        date: Optional new date in YYYY-MM-DD format.
    """
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM expenses WHERE id = ?", (expense_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return f"Error: Expense with ID {expense_id} does not exist."

        updates = []
        params = []

        if amount is not None:
            if amount <= 0:
                return "Error: Amount must be greater than zero."
            updates.append("amount = ?")
            params.append(amount)

        if category is not None:
            category = category.strip()
            if not category:
                return "Error: Category cannot be empty."
            updates.append("category = ?")
            params.append(category)

        if subcategory is not None:
            val = subcategory.strip() if subcategory.strip() else None
            updates.append("subcategory = ?")
            params.append(val)

        if note is not None:
            val = note.strip() if note.strip() else None
            updates.append("note = ?")
            params.append(val)

        if date is not None:
            try:
                datetime.strptime(date, "%Y-%m-%d")
                updates.append("date = ?")
                params.append(date)
            except ValueError:
                return "Error: Date must be in YYYY-MM-DD format."

        if not updates:
            return "No fields provided to update."

        params.append(expense_id)
        query = f"UPDATE expenses SET {', '.join(updates)} WHERE id = ?"
        await db.execute(query, params)
        await db.commit()

    return f"Success: Expense with ID {expense_id} has been updated."


@mcp.tool()
async def delete_expense(expense_id: int) -> str:
    """Delete an expense from the database by ID.

    Args:
        expense_id: The ID of the expense to delete.
    """
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM expenses WHERE id = ?", (expense_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return f"Error: Expense with ID {expense_id} does not exist."

        await db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        await db.commit()

    return f"Success: Expense with ID {expense_id} has been deleted."


@mcp.tool()
async def list_expenses(
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> str:
    """List and filter recorded expenses.

    Args:
        category: Optional category to filter by.
        subcategory: Optional subcategory to filter by.
        start_date: Optional start date (YYYY-MM-DD) for filtering.
        end_date: Optional end date (YYYY-MM-DD) for filtering.
        limit: Maximum number of expenses to return. Defaults to 50.
    """
    query = "SELECT id, date, amount, category, subcategory, note FROM expenses WHERE 1=1"
    params: list = []

    if category:
        query += " AND category = ?"
        params.append(category.strip())

    if subcategory:
        query += " AND subcategory = ?"
        params.append(subcategory.strip())

    if start_date:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            query += " AND date >= ?"
            params.append(start_date)
        except ValueError:
            return "Error: start_date must be in YYYY-MM-DD format."

    if end_date:
        try:
            datetime.strptime(end_date, "%Y-%m-%d")
            query += " AND date <= ?"
            params.append(end_date)
        except ValueError:
            return "Error: end_date must be in YYYY-MM-DD format."

    query += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(limit)

    async with get_db() as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

    if not rows:
        return "No expenses found matching the criteria."

    output = [
        f"{'ID':<5} | {'Date':<10} | {'Amount':<10} | {'Category':<15} | {'Subcategory':<15} | {'Note'}"
    ]
    output.append("-" * 75)

    for row in rows:
        subcat = row["subcategory"] if row["subcategory"] else "-"
        note = row["note"] if row["note"] else "-"
        output.append(
            f"{row['id']:<5} | {row['date']:<10} | {row['amount']:<10.2f} | "
            f"{row['category']:<15} | {subcat:<15} | {note}"
        )

    return "\n".join(output)


@mcp.tool()
async def summarize(
    group_by: str = "category",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """Summarize expenses by category, subcategory, or month.

    Args:
        group_by: Field to group summaries by. Options: 'category', 'subcategory', 'month'.
        start_date: Optional start date (YYYY-MM-DD) to filter by.
        end_date: Optional end date (YYYY-MM-DD) to filter by.
    """
    valid_groups = ["category", "subcategory", "month"]
    group_by = group_by.lower().strip()
    if group_by not in valid_groups:
        return f"Error: group_by must be one of {valid_groups}"

    total_query = "SELECT SUM(amount) as total, COUNT(*) as count FROM expenses WHERE 1=1"
    params: list = []

    if start_date:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            total_query += " AND date >= ?"
            params.append(start_date)
        except ValueError:
            return "Error: start_date must be in YYYY-MM-DD format."

    if end_date:
        try:
            datetime.strptime(end_date, "%Y-%m-%d")
            total_query += " AND date <= ?"
            params.append(end_date)
        except ValueError:
            return "Error: end_date must be in YYYY-MM-DD format."

    async with get_db() as db:
        cursor = await db.execute(total_query, params)
        total_row = await cursor.fetchone()

    if not total_row or total_row["total"] is None or total_row["count"] == 0:
        return "No expenses found to summarize."

    total_amount = total_row["total"]
    total_count = total_row["count"]

    if group_by == "category":
        group_sql = "category"
        group_column_label = "Category"
    elif group_by == "subcategory":
        group_sql = "COALESCE(subcategory, 'Uncategorized') || ' (' || category || ')'"
        group_column_label = "Subcategory (Category)"
    else:  # month
        group_sql = "SUBSTR(date, 1, 7)"
        group_column_label = "Month (YYYY-MM)"

    group_query = f"""
        SELECT
            {group_sql} as grp,
            SUM(amount) as sub_total,
            COUNT(*) as sub_count
        FROM expenses
        WHERE 1=1
    """
    group_params: list = []
    if start_date:
        group_query += " AND date >= ?"
        group_params.append(start_date)
    if end_date:
        group_query += " AND date <= ?"
        group_params.append(end_date)
    group_query += " GROUP BY grp ORDER BY sub_total DESC"

    async with get_db() as db:
        cursor = await db.execute(group_query, group_params)
        rows = await cursor.fetchall()

    output = ["=== EXPENSE SUMMARY ==="]
    filter_info = []
    if start_date:
        filter_info.append(f"From: {start_date}")
    if end_date:
        filter_info.append(f"To: {end_date}")
    if filter_info:
        output.append(" | ".join(filter_info))

    output.append(f"Total Amount Spent: {total_amount:.2f}")
    output.append(f"Total Transactions: {total_count}")
    output.append(f"Average Transaction: {total_amount / total_count:.2f}")
    output.append("")
    output.append(
        f"{group_column_label:<30} | {'Total Amount':<12} | {'Percentage':<10} | {'Count'}"
    )
    output.append("-" * 65)

    for row in rows:
        percentage = (row["sub_total"] / total_amount) * 100
        output.append(
            f"{row['grp']:<30} | {row['sub_total']:<12.2f} | {percentage:<9.1f}% | {row['sub_count']}"
        )

    return "\n".join(output)


@mcp.tool()
async def set_budget(category: str, limit_amount: float) -> str:
    """Set or update a monthly budget limit for a specific category.

    Args:
        category: The category name (e.g., Food, Travel, Shopping).
        limit_amount: The monthly spending limit (must be greater than zero).
    """
    category = category.strip()
    if not category:
        return "Error: Category cannot be empty."
    if limit_amount <= 0:
        return "Error: Budget limit amount must be greater than zero."

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO budgets (category, limit_amount)
            VALUES (?, ?)
            ON CONFLICT(category) DO UPDATE SET limit_amount = excluded.limit_amount
            """,
            (category, limit_amount),
        )
        await db.commit()

    return f"Success: Budget for Category '{category}' set to {limit_amount:.2f} per month."


@mcp.tool()
async def check_budget(month: Optional[str] = None) -> str:
    """Check budget status (spent vs budget limit) for a given month.

    Args:
        month: Optional month in YYYY-MM format. Defaults to current month.
    """
    if month:
        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            return "Error: Month must be in YYYY-MM format."
    else:
        month = datetime.now().strftime("%Y-%m")

    async with get_db() as db:
        cursor = await db.execute("SELECT category, limit_amount FROM budgets")
        budget_rows = await cursor.fetchall()
        budgets = {row["category"]: row["limit_amount"] for row in budget_rows}

        cursor = await db.execute(
            """
            SELECT category, SUM(amount) as total_spent
            FROM expenses
            WHERE SUBSTR(date, 1, 7) = ?
            GROUP BY category
            """,
            (month,),
        )
        spent_rows = await cursor.fetchall()
        spent = {row["category"]: row["total_spent"] for row in spent_rows}

    if not budgets and not spent:
        return f"No budgets set or expenses found for month {month}."

    all_categories = sorted(set(list(budgets.keys()) + list(spent.keys())))

    output = [f"=== BUDGET STATUS FOR {month} ==="]
    output.append(
        f"{'Category':<20} | {'Budget Limit':<12} | {'Actual Spent':<12} | "
        f"{'Remaining':<12} | {'Usage %':<9} | {'Status'}"
    )
    output.append("-" * 88)

    for cat in all_categories:
        limit = budgets.get(cat, 0.0)
        actual = spent.get(cat, 0.0)
        remaining = limit - actual

        limit_str = f"{limit:.2f}" if limit > 0 else "-"
        remaining_str = f"{remaining:.2f}" if limit > 0 else "-"

        if limit > 0:
            usage_pct = (actual / limit) * 100
            usage_str = f"{usage_pct:.1f}%"
            if usage_pct > 100:
                status = f"OVER BUDGET by {abs(remaining):.2f}!"
            elif usage_pct >= 90:
                status = "Critical (>=90%)"
            elif usage_pct >= 75:
                status = "Warning (>=75%)"
            else:
                status = "OK"
        else:
            usage_str = "-"
            status = "No Limit Set"

        output.append(
            f"{cat:<20} | {limit_str:>12} | {actual:>12.2f} | "
            f"{remaining_str:>12} | {usage_str:>9} | {status}"
        )

    return "\n".join(output)


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Always run over stdio for local use with langchain-mcp-adapters
    mcp.run(transport="stdio")
