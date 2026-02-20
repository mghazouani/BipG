# ADR-0001-architecture-baseline

## Context

LIV POC is a Docker-based proof of concept for delivery missions and live tracking. The system spans an Odoo backoffice, a FastAPI service, Redis for real-time state, and Flutter apps for client/driver.

We need a shared baseline that clarifies:

- the primary system boundaries,
- the source of truth for delivery entities,
- how real-time tracking is ingested and persisted.

## Decision

Adopt the following architecture baseline:

- **Odoo 17** is the backoffice and **system of record** for deliveries/missions and persisted tracking snapshots.
- **FastAPI** provides:
  - REST endpoints for client/backoffice/driver workflows,
  - WebSocket ingestion for real-time tracking.
- **Redis** is used for:
  - last-known tracking state and fast reads,
  - pub/sub for real-time updates,
  - transient caching to support resilience when Odoo is temporarily unavailable.
- **Flutter apps** consume FastAPI:
  - `liv_client_app` for client/order flow (POC),
  - `liv_driver_app` for active mission and tracking.

Repository mapping:

- `backend-fastapi/` (FastAPI)
- `odoo-addon/` (Odoo addon)
- `liv_client_app/` (Flutter client)
- `liv_driver_app/` (Flutter driver)
- `docs/` (documentation)

## Alternatives considered

- **FastAPI as system of record** (store deliveries in FastAPI DB and sync to Odoo): adds reconciliation complexity for a POC.
- **No Redis** (direct writes/reads to Odoo only): increases latency and reduces resilience for high-frequency tracking.
- **Push tracking directly to Odoo**: higher coupling and load; less suitable for real-time ingestion.

## Consequences

- Odoo schema changes are the primary driver for persisted delivery/tracking data.
- FastAPI must maintain reliable integration with Odoo and handle transient Odoo failures gracefully.
- Redis becomes a critical dependency for real-time performance and resilience (still not the long-term source of truth).

## Follow-ups

- Keep `docs/ARCHITECTURE.md` aligned with this baseline as flows evolve.
- Add additional ADRs when major decisions change (auth, persistence, deployment, etc.).

