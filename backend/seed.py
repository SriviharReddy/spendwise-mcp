"""Deterministic database seed script for SpendWise showcase demonstration."""

import asyncio
from datetime import date
from typing import Any
import aiosqlite

from backend.config import DB_PATH, logger
from backend.db import init_db


async def seed_database() -> dict[str, Any]:
    """Resets and populates the SQLite database with realistic demonstration data."""
    await init_db()

    today = date.today()
    current_year = today.year
    current_month = today.month

    # Generate dates relative to today
    def date_in_current_month(day_num: int) -> str:
        # Clamp day to current day or max 28
        safe_day = max(1, min(day_num, 28))
        return f"{current_year:04d}-{current_month:02d}-{safe_day:02d}"

    def date_in_prev_month(day_num: int) -> str:
        if current_month == 1:
            p_year = current_year - 1
            p_month = 12
        else:
            p_year = current_year
            p_month = current_month - 1
        safe_day = max(1, min(day_num, 28))
        return f"{p_year:04d}-{p_month:02d}-{safe_day:02d}"

    # 1. Category Budgets
    budgets = [
        ("Food", 650.00),
        ("Housing", 1850.00),
        ("Transportation", 220.00),
        ("Utilities", 180.00),
        ("Entertainment", 160.00),
        ("Shopping", 300.00),
    ]

    # 2. Realistic Expenses Dataset
    expenses = [
        # Current Month — Housing & Utilities
        (date_in_current_month(1), 1850.00, "Housing", "Rent", "Monthly apartment rent payment"),
        (date_in_current_month(3), 78.50, "Utilities", "Electric", "Clean power electric utility bill"),
        (date_in_current_month(5), 65.00, "Utilities", "Internet", "Fiber optic gigabit internet"),
        (date_in_current_month(7), 45.00, "Utilities", "Mobile", "Unlimited cell phone plan"),

        # Current Month — Food & Dining
        (date_in_current_month(2), 94.50, "Food", "Groceries", "Weekly grocery run at Trader Joe's"),
        (date_in_current_month(4), 18.40, "Food", "Lunch", "Warm grain bowl at Sweetgreen"),
        (date_in_current_month(6), 6.25, "Food", "Coffee", "Oat latte at Blue Bottle"),
        (date_in_current_month(8), 62.10, "Food", "Groceries", "Organic produce & snacks at Whole Foods"),
        (date_in_current_month(10), 85.00, "Food", "Dining", "Dinner with partner at Nobu"),
        (date_in_current_month(12), 12.50, "Food", "Bakery", "Sourdough bread and pastries"),
        (date_in_current_month(14), 34.00, "Food", "Dinner", "Artisanal pizza night"),
        (date_in_current_month(16), 16.80, "Food", "Lunch", "Burrito bowl at Chipotle"),
        (date_in_current_month(18), 45.20, "Food", "Groceries", "Pantry staples and fruit"),
        (date_in_current_month(20), 7.50, "Food", "Coffee", "Matcha latte"),

        # Current Month — Transportation
        (date_in_current_month(3), 42.00, "Transportation", "Rideshare", "Uber to international airport"),
        (date_in_current_month(9), 30.00, "Transportation", "Transit", "Monthly metro card transit pass"),
        (date_in_current_month(13), 48.50, "Transportation", "Fuel", "Gas station full tank fill-up"),
        (date_in_current_month(17), 18.20, "Transportation", "Rideshare", "Lyft ride back from downtown"),
        (date_in_current_month(21), 15.00, "Transportation", "Parking", "City center parking garage"),

        # Current Month — Entertainment & Subscriptions
        (date_in_current_month(2), 19.99, "Entertainment", "Streaming", "Netflix 4K subscription"),
        (date_in_current_month(4), 16.99, "Entertainment", "Music", "Spotify Family streaming plan"),
        (date_in_current_month(11), 32.00, "Entertainment", "Movies", "IMAX theater movie tickets"),
        (date_in_current_month(15), 45.00, "Entertainment", "Games", "Board game night purchase"),

        # Current Month — Shopping & Health
        (date_in_current_month(5), 55.00, "Health", "Fitness", "Monthly gym membership"),
        (date_in_current_month(8), 54.20, "Shopping", "Online", "Amazon household essentials"),
        (date_in_current_month(14), 88.00, "Shopping", "Clothing", "Uniqlo casual apparel"),
        (date_in_current_month(19), 24.50, "Shopping", "Books", "Technical AI engineering book"),
        (date_in_current_month(22), 22.40, "Health", "Pharmacy", "Vitamins and first-aid supplies"),

        # Previous Month — Historical Records for Trend Comparison
        (date_in_prev_month(1), 1850.00, "Housing", "Rent", "Monthly apartment rent payment"),
        (date_in_prev_month(3), 82.10, "Utilities", "Electric", "Electric utility bill"),
        (date_in_prev_month(5), 65.00, "Utilities", "Internet", "Fiber internet"),
        (date_in_prev_month(8), 410.00, "Food", "Groceries & Dining", "Combined food spending"),
        (date_in_prev_month(12), 145.00, "Transportation", "Transit & Gas", "Combined commute"),
        (date_in_prev_month(15), 120.00, "Entertainment", "Subscriptions & Events", "Concert & streaming"),
        (date_in_prev_month(20), 210.00, "Shopping", "Retail", "Home improvement supplies"),
    ]

    async with aiosqlite.connect(DB_PATH) as db:
        # Clear existing data
        await db.execute("DELETE FROM expenses")
        await db.execute("DELETE FROM budgets")

        # Insert Budgets
        await db.executemany(
            "INSERT INTO budgets (category, limit_amount) VALUES (?, ?)",
            budgets,
        )

        # Insert Expenses
        await db.executemany(
            """
            INSERT INTO expenses (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            expenses,
        )

        await db.commit()

    logger.info(
        "Seeded database with %d budgets and %d expenses.",
        len(budgets),
        len(expenses),
    )

    return {
        "success": True,
        "seeded_budgets": len(budgets),
        "seeded_expenses": len(expenses),
    }


if __name__ == "__main__":
    result = asyncio.run(seed_database())
    print("Seed result:", result)
