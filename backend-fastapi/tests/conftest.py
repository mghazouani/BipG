"""Pytest conftest: ensure app package is importable when running from backend-fastapi root."""
import sys
from pathlib import Path

import httpx
import pytest

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.main import app


@pytest.fixture
async def client():
    """Async test client using ASGITransport (no httpx app= deprecation)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
