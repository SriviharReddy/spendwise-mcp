"""SpendWise AI - FastAPI Application Entrypoint & Static UI Server."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import FRONTEND_DIR, logger, settings
from backend.db import init_db
from backend.routes.api import router as api_router
from backend.routes.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager: runs startup and shutdown tasks."""
    logger.info("Starting SpendWise AI Backend...")
    # Ensure frontend directory exists
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
    # Initialize database
    await init_db()
    logger.info("SpendWise AI Backend initialized on port %d", settings.port)
    yield
    logger.info("Shutting down SpendWise AI Backend...")


app = FastAPI(
    title="SpendWise AI — MCP Agent Showcase",
    description="Decoupled Agentic Financial Intelligence Hub backed by FastMCP & SQLite.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for development and local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(api_router)
app.include_router(chat_router)

# Mount Static UI files at root
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
