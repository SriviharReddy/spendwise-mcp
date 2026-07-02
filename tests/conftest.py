"""Pytest configuration and shared fixtures for SpendWise test suite."""

import asyncio
from typing import Generator
import pytest
from fastapi.testclient import TestClient

from backend.db import init_db
from backend.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initializes SQLite schema before running tests."""
    asyncio.run(init_db())
    yield


@pytest.fixture(scope="function")
def client() -> Generator[TestClient, None, None]:
    """Provides a FastAPI TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client
