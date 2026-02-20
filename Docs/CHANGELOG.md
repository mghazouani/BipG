# Changelog

All notable changes to this POC should be documented in this file.

## 2026-02-20 — CI, Flutter health badge, Odoo Backend Status

- Added:
  - `.github/workflows/backend.yml`: GitHub Actions CI — Python 3.11, `pip install`, `pytest tests/test_health_status.py` (10 tests, triggered on `backend-fastapi/**`).
  - `.github/workflows/flutter.yml`: GitHub Actions CI — Flutter stable, `flutter pub get` + `flutter analyze` for both `liv_driver_app` and `liv_client_app` (matrix, triggered on each app path).
  - `liv_driver_app/lib/services/health_service.dart`: `HealthService` singleton — `GET /health`, returns `HealthResult { reachable, latencyMs, error }`, timeout 5 s.
  - `liv_client_app/lib/services/health_service.dart`: idem.
  - `_HealthBadge` widget in `DriverHomeScreen` and `OrderScreen`: tap-to-refresh badge "Backend: OK (Xms)" / "Backend: Down", loaded on `initState`.
  - `odoo-addon/liv_delivery/models/backend_health.py`: abstract model `liv.backend.health` + `LivBackendHealthDisplay` (TransientModel) — cron calls `/health/status`, stores result in `ir.config_parameter`, display model exposes status/updated/message/base_url without secret.
  - `odoo-addon/liv_delivery/data/backend_health_cron.xml`: scheduled action "LIV: Check Backend Health" every 5 minutes.
  - `odoo-addon/liv_delivery/views/backend_health_views.xml`: form view + server action + menuitem **LIV → Backend Status** (secret never displayed).
  - `backend-fastapi/app/main.py`: `GET /health/status` secured by `HEALTH_SECRET` (Bearer or `X-Health-Token`); returns `ok/redis/odoo/ts` with `ts` in ISO-8601 UTC (`...Z`), 401 on bad token, 503 when `ok=false`.
  - `backend-fastapi/tests/test_health_status.py`: 10 unit tests (200/401/503, mocked redis + odoo).
  - `odoo.conf`: `db_host/db_port/db_user/db_password/addons_path` — DB config implicit for all Odoo CLI commands.
  - `docs/runbooks/odoo-conf.md`: runbook odoo.conf + upgrade command.
- Changed:
  - `docker-compose.yml`: mount `./odoo.conf:/etc/odoo/odoo.conf:ro`, removed redundant `environment: HOST/USER/PASSWORD` on odoo service; added `volumes: ./backend-fastapi:/app` on fastapi service.
  - `README.md`: stack table, CI table, badge placeholders, Run tests section.
- Validated (2026-02-20):
  - `pytest` 10/10 PASS in FastAPI container.
  - `flutter analyze` 0 issues on both apps.
  - Odoo cron → `liv.backend_health_status = ok`, `liv.backend_health_updated` timestamp set.
  - LIV → Backend Status: 4 fields only, no secret visible.
  - Backend boot: `WS_SECRET` is required (CI must set it; a dummy is fine for unit tests).

## 2026-02-20 — Odoo config and model-level stability fixes
- Added:
  - `odoo.conf`: `data_dir = /var/lib/odoo` to keep filestore path consistent.
- Changed:
  - `odoo.conf`: ensured `db_host = db` so Odoo connects to Postgres over TCP (no Unix socket fallback).
  - `liv.delivery`: added `mail.thread` + `mail.activity.mixin` inheritance so `tracking=True` fields are valid.
  - `__manifest__.py`: added `mail` to `depends`.
  - `liv.delivery.track.driver_id`: made optional with `ondelete="set null"` to match existing DB state.
- Fixed:
  - Prevented module install/upgrade errors caused by `tracking=True` without mail mixins.
  - Avoided filestore inconsistencies caused by an unexpected `data_dir`.
- Notes/Risks:
  - After deploying these changes, **upgrade the module** (`liv_delivery`) so Odoo loads the updated model definitions.

## 2026-02-20 — `/health/status` timestamp normalized to ISO-8601 UTC
- Added:
  - N/A
- Changed:
  - `/health/status` now returns `ts` as an ISO-8601 UTC string (`...Z`) instead of a float.
- Fixed:
  - Updated unit test to assert `ts` is an ISO string (contains `T` and ends with `Z`).
- Notes/Risks:
  - **Backward-incompatible** for consumers expecting a numeric timestamp; update clients/parsers accordingly.

## 2026-02-19 — DocKeeper spec moved to Cursor agents
- Added:
  - `.cursor/agents/dockeeper.md` (DocKeeper subagent spec)
  - `docs/adr/ADR-0001-architecture-baseline.md`
  - `docs/adr/ADR-0002-dockeeper-subagent.md`
  - `docs/runbooks/backend-health.md`
- Changed:
  - Updated references to point to `.cursor/agents/dockeeper.md`
  - Normalized documentation paths to `docs/` (lowercase) in references
- Fixed:
  - N/A
- Notes/Risks:
  - Path is outside `liv-poc/`; keep in mind when packaging/copying the project folder.

## YYYY-MM-DD — <Short title>
- Added:
- Changed:
- Fixed:
- Notes/Risks:

