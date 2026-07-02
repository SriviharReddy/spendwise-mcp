"""System prompt builder with dynamic MCP resource injection."""

from datetime import date


def build_system_prompt(categories_json: str, today_str: str | None = None) -> str:
    """Constructs the system prompt injecting current date and dynamic categories resource.

    Args:
        categories_json: Raw JSON string of the categories://list FastMCP resource.
        today_str: Optional ISO date string (defaults to today).

    Returns:
        Structured system prompt string for the LangChain agent.
    """
    date_context = today_str or date.today().isoformat()
    return (
        "You are SpendWise AI, an expert agentic financial assistant.\n"
        "You have direct access to tools for managing expenses, setting budgets, checking budget health, and generating financial summaries.\n\n"
        f"Today's date is: {date_context}.\n"
        f"Valid Category Taxonomy:\n{categories_json}\n\n"
        "Guidelines:\n"
        "- When the user asks to log, add, edit, or delete an expense, call the appropriate tool.\n"
        "- When the user asks about budgets or summaries, use check_budget or summarize.\n"
        "- Always provide clear, helpful, and concise markdown answers with currency formatting ($XX.XX).\n"
    )
