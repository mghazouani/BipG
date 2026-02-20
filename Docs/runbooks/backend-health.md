# Backend health (Odoo addon)

## Purpose

This runbook describes the **backend health check** implemented in the Odoo addon (LIV) to validate connectivity and configuration toward the backend services used by the POC.

## Where it lives

- Odoo addon: `odoo-addon/`
- Health logic: `odoo-addon/liv_delivery/models/backend_health.py`
- Odoo config: `odoo.conf` (see `docs/runbooks/odoo-conf.md`)
- UI action/menu: `odoo-addon/liv_delivery/views/backend_health_views.xml`

## What it checks (high level)

- Calls FastAPI `GET /health/status` (secured) and stores the latest status in Odoo system parameters.
- Interprets `ok/redis/odoo/ts/message` and maps them to:
  - `ok` / `degraded` / `down` / `auth_error`
- Never reads or displays the secret in the UI.

## How to use (manual)

### 1) Upgrade Odoo module

- Odoo Apps → **LIV Delivery Tracking** → **Upgrade**
- Or via CLI (DB config is implicit from `odoo.conf`):

```bash
docker compose exec odoo odoo -u liv_delivery --stop-after-init
```

### 2) Configure Odoo system parameters

Settings → Technical → Parameters → System Parameters:

- `liv.fastapi_base_url`
  - For Docker Compose: set to `http://fastapi:8000` (Odoo container → FastAPI service)
- `liv.health_secret`
  - Must match FastAPI `HEALTH_SECRET` (used as `Authorization: Bearer …` to call `/health/status`)

### 3) Validate UI: “LIV → Backend Status”

- Open **LIV → Backend Status**
- What it shows:
  - `status` (`ok` / `degraded` / `down` / `auth_error`)
  - `updated` (FastAPI `ts`, ISO-8601 UTC string ending with `Z`)
  - `base_url`
  - `message`

### 4) Validate the backend endpoint (unit test)

Run the FastAPI unit test for `/health/status`:

```bash
docker compose exec fastapi python -m pytest -v tests/test_health_status.py
```

## Operational notes

- Prefer non-production endpoints during POC testing.
- Do not paste secrets/tokens into tickets or docs.
- If errors occur, capture:
  - timestamp,
  - Odoo user / company context,
  - error reason (sanitized),
  - backend URL (non-secret).

## Troubleshooting (quick)

- **`auth_error`**: `liv.health_secret` mismatch or FastAPI `HEALTH_SECRET` missing/empty.
- **`down` + “Missing liv.fastapi_base_url”**: set `liv.fastapi_base_url`.
- **`down` + “Connection error: …”**: base URL unreachable from Odoo (wrong host/port/scheme, service/network down).
- **`degraded`**: check `/health/status` payload to see whether `redis=false` or `odoo=false`.

