# Architecture

## Overview

LIV POC is a Docker-based system combining:

- **Odoo 17**: Backoffice and system of record for deliveries/missions and tracking snapshots.
- **FastAPI**: API surface for client/driver apps and real-time tracking ingestion.
- **Postgres**: Primary database for Odoo.
- **Redis**: Cache + real-time tracking state / pubsub (and resilience support when Odoo is unavailable).
- **Flutter apps**:
  - `liv_client_app`: customer/client-facing app (order → mission lifecycle).
  - `liv_driver_app`: driver-facing app (active mission + tracking).

## Repository structure

- `backend-fastapi/`: FastAPI service.
- `odoo-addon/`: Odoo addon(s) for LIV delivery tracking.
- `liv_client_app/`: Flutter client application.
- `liv_driver_app/`: Flutter driver application.
- `docs/`: project documentation (this folder).
- `odoo.conf`: Odoo configuration (DB + addons), mounted into the Odoo container.

## Core flows (high level)

- **Backoffice creates/assigns missions** in Odoo (deliveries).
- **Client app** interacts with FastAPI to place orders and initiate mission creation (POC flow).
- **Driver app** queries FastAPI for the active mission and sends location updates.
- **FastAPI** validates and processes tracking, writes last known state to Redis, and periodically persists snapshots/last_* to Odoo.

## Driver actions by state (driver app)

The driver app exposes mission actions that map to the Odoo delivery state machine. State validity is enforced server-side (FastAPI/Odoo); the UI buttons trigger the transition endpoints.

| Current state | Driver action | Backend call(s) | Next state |
|---|---|---|---|
| `assigned` | **Start** | `POST /deliveries/{id}/state` `{state:"en_route"}` | `en_route` |
| `en_route` | **Arrive** | `POST /deliveries/{id}/state` `{state:"arrived"}` | `arrived` |
| `en_route` / `arrived` | **Deliver + Cash** | `POST /deliveries/{id}/collect-payment` then `POST /deliveries/{id}/state` `{state:"delivered"}` | `delivered` |
| `assigned` / `en_route` / `arrived` | **Start Tracking** | `WS /ws/track?token=...` (tracking accepted only in active states) | (no state change) |
| `delivered` / `cancelled` | (no operational actions expected) | — | — |

## Integration notes

- **FastAPI ↔ Odoo**: synchronous validation and writes where possible; resilience mechanisms may queue writes when Odoo is unavailable.
- **Redis**: used for caching, throttling/back-pressure, and last-known tracking state.

## Health checks (FastAPI + Odoo)

- **`GET /health`**: unauthenticated liveness probe (`{"ok": true}`).
- **`GET /health/status`**: authenticated dependency status (requires `HEALTH_SECRET` via `Authorization: Bearer …` or `X-Health-Token`).
  - Returns `ok/redis/odoo/ts` and uses HTTP 503 when `ok=false`.
- Odoo periodically calls `/health/status` (scheduled action) and exposes results in **LIV → Backend Status**.

## Security & configuration (documentation-level)

- Do not commit secrets. Keep environment values (e.g., WebSocket secrets) in `.env` or environment variables only.
- When documenting changes, avoid including tokens, secrets, or production values.

