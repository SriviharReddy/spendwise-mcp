"""SpendWise AI — Application Launcher.

Launches the unified FastAPI backend & frontend showcase.
Usage:
    uv run python app.py
    # or
    uv run uvicorn backend.main:app --reload
"""

import uvicorn
from backend.config import settings

if __name__ == "__main__":
    print("=" * 70)
    print("⚡ SpendWise AI — MCP Agent Showcase & Observability Hub")
    print(f"🚀 Serving Unified App at: http://localhost:{settings.port}")
    print(f"📡 API Health Endpoint:   http://localhost:{settings.port}/api/health")
    print("=" * 70)
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
