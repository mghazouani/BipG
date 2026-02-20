"""Unit tests for POST /deliveries/{id}/state — state machine guardrails (Story #1).

Tests cover:
- 422 on unknown state
- 404 when delivery not found
- 422 on invalid transition (e.g. draft→delivered, terminal→any)
- 200 on every valid transition
- 503 when Odoo is unavailable
"""
import pytest
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _delivery(state: str) -> dict:
    return {"id": 1, "state": state, "driver_id": 2, "customer_name": "Test"}


def _post_state(client, delivery_id: int, state: str):
    return client.post(
        f"/deliveries/{delivery_id}/state",
        json={"state": state},
    )


# ---------------------------------------------------------------------------
# Unknown / invalid state value
# ---------------------------------------------------------------------------

async def test_unknown_state_returns_422(client):
    """A state value not in the state machine returns 422 immediately (no Odoo call)."""
    r = await _post_state(client, 1, "flying")
    assert r.status_code == 422
    data = r.json()
    assert data["detail"]["error"] == "unknown_state"
    assert "flying" == data["detail"]["requested"]
    assert "draft" in data["detail"]["valid_states"]


# ---------------------------------------------------------------------------
# 404 — delivery not found
# ---------------------------------------------------------------------------

async def test_delivery_not_found_returns_404(client):
    with (
        patch("app.main.login_uid", AsyncMock(return_value=1)),
        patch("app.main.read_delivery", AsyncMock(return_value=None)),
    ):
        r = await _post_state(client, 999, "assigned")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 503 — Odoo unavailable
# ---------------------------------------------------------------------------

async def test_odoo_down_returns_503(client):
    with patch("app.main.login_uid", AsyncMock(side_effect=Exception("timeout"))):
        r = await _post_state(client, 1, "assigned")
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# 422 — invalid transitions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("current,requested", [
    ("draft",     "en_route"),
    ("draft",     "arrived"),
    ("draft",     "delivered"),
    ("assigned",  "draft"),
    ("assigned",  "arrived"),
    ("assigned",  "delivered"),
    ("en_route",  "draft"),
    ("en_route",  "assigned"),
    ("arrived",   "draft"),
    ("arrived",   "assigned"),
    ("arrived",   "en_route"),
    ("delivered", "assigned"),
    ("delivered", "en_route"),
    ("delivered", "cancelled"),
    ("cancelled", "draft"),
    ("cancelled", "assigned"),
    ("cancelled", "delivered"),
    # missing from initial suite — cancelled can also not go to en_route/arrived
    ("cancelled", "en_route"),
    ("cancelled", "arrived"),
    # self-transitions are invalid (idempotent write bypassed intentionally)
    ("draft",     "draft"),
    ("assigned",  "assigned"),
    ("en_route",  "en_route"),
    ("arrived",   "arrived"),
    ("delivered", "delivered"),
    ("cancelled", "cancelled"),
])
async def test_invalid_transition_returns_422(client, current, requested):
    with (
        patch("app.main.login_uid", AsyncMock(return_value=1)),
        patch("app.main.read_delivery", AsyncMock(return_value=_delivery(current))),
    ):
        r = await _post_state(client, 1, requested)
    assert r.status_code == 422, f"Expected 422 for {current}→{requested}, got {r.status_code}"
    data = r.json()
    assert data["detail"]["error"] == "invalid_transition"
    assert data["detail"]["current"] == current
    assert data["detail"]["requested"] == requested


# ---------------------------------------------------------------------------
# 200 — valid transitions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("current,requested", [
    ("draft",    "assigned"),
    ("draft",    "cancelled"),
    ("assigned", "en_route"),
    ("assigned", "cancelled"),
    ("en_route", "arrived"),
    ("en_route", "delivered"),
    ("en_route", "cancelled"),
    ("arrived",  "delivered"),
    ("arrived",  "cancelled"),
])
async def test_valid_transition_returns_200(client, current, requested):
    with (
        patch("app.main.login_uid", AsyncMock(return_value=1)),
        patch("app.main.read_delivery", AsyncMock(return_value=_delivery(current))),
        patch("app.main.set_delivery_state", AsyncMock(return_value=None)),
    ):
        r = await _post_state(client, 1, requested)
    assert r.status_code == 200, f"Expected 200 for {current}→{requested}, got {r.status_code}"
    data = r.json()
    assert data["delivery_id"] == 1
    assert data["state"] == requested
