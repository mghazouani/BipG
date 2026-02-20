"""Unit tests for GET /health/status: 200, 401, 503 with mocked redis and odoo."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


pytestmark = pytest.mark.anyio


@pytest.fixture
def valid_token():
    return "test-health-secret"


async def test_health_status_401_no_token(client):
    """Missing token returns 401."""
    r = await client.get("/health/status")
    assert r.status_code == 401


async def test_health_status_401_invalid_token(client):
    """Wrong token returns 401."""
    with patch("app.main.HEALTH_SECRET", "test-health-secret"):
        r = await client.get("/health/status", headers={"Authorization": "Bearer wrong-token"})
    assert r.status_code == 401


async def test_health_status_401_empty_secret_rejects_any_token(client):
    """When HEALTH_SECRET is empty, any token is invalid."""
    with patch("app.main.HEALTH_SECRET", ""):
        r = await client.get("/health/status", headers={"X-Health-Token": "anything"})
    assert r.status_code == 401


async def test_health_status_200_bearer(client, valid_token):
    """Valid Bearer token with redis and odoo up returns 200 and ok=true."""
    with (
        patch("app.main.HEALTH_SECRET", valid_token),
        patch("app.main.redis", MagicMock(ping=AsyncMock(return_value=True))),
        patch("app.main.login_uid", AsyncMock(return_value=1)),
    ):
        r = await client.get("/health/status", headers={"Authorization": f"Bearer {valid_token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["redis"] is True
    assert data["odoo"] is True
    assert isinstance(data.get("ts"), str)
    assert "T" in data["ts"]
    assert data["ts"].endswith("Z")
    assert "message" not in data


async def test_health_status_200_x_health_token(client, valid_token):
    """Valid X-Health-Token header with redis and odoo up returns 200."""
    with (
        patch("app.main.HEALTH_SECRET", valid_token),
        patch("app.main.redis", MagicMock(ping=AsyncMock(return_value=True))),
        patch("app.main.login_uid", AsyncMock(return_value=1)),
    ):
        r = await client.get("/health/status", headers={"X-Health-Token": valid_token})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["redis"] is True
    assert data["odoo"] is True


async def test_health_status_503_redis_down(client, valid_token):
    """Valid token but redis down returns 503 and ok=false, redis=false."""
    with (
        patch("app.main.HEALTH_SECRET", valid_token),
        patch("app.main.redis", MagicMock(ping=AsyncMock(side_effect=Exception("connection refused")))),
        patch("app.main.login_uid", AsyncMock(return_value=1)),
    ):
        r = await client.get("/health/status", headers={"Authorization": f"Bearer {valid_token}"})
    assert r.status_code == 503
    data = r.json()
    assert data["ok"] is False
    assert data["redis"] is False
    assert data["odoo"] is True
    assert "message" in data
    assert "redis" in data["message"].lower()


async def test_health_status_503_odoo_down(client, valid_token):
    """Valid token but odoo down returns 503 and ok=false, odoo=false."""
    with (
        patch("app.main.HEALTH_SECRET", valid_token),
        patch("app.main.redis", MagicMock(ping=AsyncMock(return_value=True))),
        patch("app.main.login_uid", AsyncMock(side_effect=Exception("Odoo unreachable"))),
    ):
        r = await client.get("/health/status", headers={"Authorization": f"Bearer {valid_token}"})
    assert r.status_code == 503
    data = r.json()
    assert data["ok"] is False
    assert data["redis"] is True
    assert data["odoo"] is False
    assert "message" in data
    assert "odoo" in data["message"].lower()


async def test_health_status_503_both_down(client, valid_token):
    """Valid token but both redis and odoo down returns 503."""
    with (
        patch("app.main.HEALTH_SECRET", valid_token),
        patch("app.main.redis", MagicMock(ping=AsyncMock(side_effect=Exception()))),
        patch("app.main.login_uid", AsyncMock(side_effect=Exception())),
    ):
        r = await client.get("/health/status", headers={"X-Health-Token": valid_token})
    assert r.status_code == 503
    data = r.json()
    assert data["ok"] is False
    assert data["redis"] is False
    assert data["odoo"] is False
    assert "message" in data


async def test_health_status_503_redis_none(client, valid_token):
    """When redis is None (not connected), redis check is false -> 503 if odoo up."""
    with (
        patch("app.main.HEALTH_SECRET", valid_token),
        patch("app.main.redis", None),
        patch("app.main.login_uid", AsyncMock(return_value=1)),
    ):
        r = await client.get("/health/status", headers={"Authorization": f"Bearer {valid_token}"})
    assert r.status_code == 503
    data = r.json()
    assert data["ok"] is False
    assert data["redis"] is False
    assert data["odoo"] is True


async def test_health_unchanged(client):
    """GET /health is unchanged and returns 200 with ok=true (no auth)."""
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
