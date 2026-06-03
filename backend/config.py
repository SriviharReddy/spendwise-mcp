"""Application configuration, logging setup, and dynamic LLM factory for SpendWise."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

# Load .env file at module import
load_dotenv()

# Base directories
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
MCP_DIR = PROJECT_ROOT / "mcp"
MCP_SERVER_PATH = MCP_DIR / "mcp-server.py"
DB_PATH = MCP_DIR / "expenses.db"
CATEGORIES_PATH = MCP_DIR / "categories.json"
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configures structured console logging with timestamp and level."""
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("spendwise")
    logger.setLevel(level)
    return logger


logger = setup_logging()


@dataclass(frozen=True)
class Settings:
    """Strongly typed application settings loaded from environment variables."""

    # Server settings
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # LLM Settings
    default_provider: str = os.getenv("LLM_PROVIDER", "deepseek").lower()

    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    google_model: str = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")

    # Paths
    mcp_server_path: Path = MCP_SERVER_PATH
    db_path: Path = DB_PATH
    categories_path: Path = CATEGORIES_PATH
    frontend_dir: Path = FRONTEND_DIR


settings = Settings()


def get_available_providers() -> list[dict[str, Any]]:
    """Returns a list of configured and available LLM providers."""
    providers = []
    providers.append({
        "id": "deepseek",
        "name": "DeepSeek",
        "default_model": settings.deepseek_model,
        "configured": bool(settings.deepseek_api_key),
    })
    providers.append({
        "id": "openai",
        "name": "OpenAI",
        "default_model": settings.openai_model,
        "configured": bool(settings.openai_api_key),
    })
    providers.append({
        "id": "gemini",
        "name": "Google Gemini",
        "default_model": settings.google_model,
        "configured": bool(settings.google_api_key),
    })
    providers.append({
        "id": "custom",
        "name": "Custom / OpenRouter",
        "default_model": "gpt-4o",
        "configured": False,
    })
    return providers


def get_chat_model(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
):
    """Instantiates a LangChain ChatModel based on requested provider, model, and optional key.

    Args:
        provider: Target provider ('deepseek', 'openai', 'gemini', 'custom'). Defaults to env setting.
        model: Specific model identifier. Defaults to provider default.
        api_key: User-supplied API key override. Defaults to env var.
        base_url: Optional custom base URL for OpenAI-compatible/Ollama/OpenRouter endpoints.

    Returns:
        A BaseChatModel instance configured with API keys.

    Raises:
        ValueError: If the required API key for the selected provider is missing.
    """
    selected_provider = (provider or settings.default_provider).lower()

    if selected_provider == "deepseek":
        resolved_key = (api_key or settings.deepseek_api_key).strip()
        if not resolved_key:
            raise ValueError(
                "DEEPSEEK_API_KEY is required. Please provide it in Settings or configure .env."
            )
        from langchain_deepseek import ChatDeepSeek

        target_base = base_url.strip() if base_url else "https://api.deepseek.com"
        return ChatDeepSeek(
            model=model or settings.deepseek_model,
            api_key=resolved_key,
            api_base=target_base,
            temperature=0.1,
            extra_body={"thinking": {"type": "disabled"}},
        )

    if selected_provider in ("openai", "custom", "openrouter"):
        resolved_key = (api_key or settings.openai_api_key).strip()
        if not resolved_key and selected_provider != "custom":
            raise ValueError(
                "OPENAI_API_KEY is required. Please provide it in Settings or configure .env."
            )
        from langchain_openai import ChatOpenAI

        target_base = base_url.strip() if base_url else None
        return ChatOpenAI(
            model=model or settings.openai_model,
            api_key=resolved_key or "sk-dummy",
            base_url=target_base,
            temperature=0.1,
        )

    if selected_provider in ("gemini", "google"):
        resolved_key = (api_key or settings.google_api_key).strip()
        if not resolved_key:
            raise ValueError(
                "GOOGLE_API_KEY is required. Please provide it in Settings or configure .env."
            )
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model or settings.google_model,
            google_api_key=resolved_key,
            temperature=0.1,
        )

    raise ValueError(f"Unsupported LLM provider: {selected_provider}")
