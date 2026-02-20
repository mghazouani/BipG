# LIV POC – Delivery tracking

Docker-based POC: Odoo 17 + Postgres + Redis + FastAPI for delivery missions and live tracking.

<!-- CI badges -->
![Backend CI](https://github.com/mghazouani/BipG/actions/workflows/backend.yml/badge.svg)
![Flutter CI](https://github.com/mghazouani/BipG/actions/workflows/flutter.yml/badge.svg)

## Stack

| Service | Technology |
|---------|-----------|
| Backoffice | Odoo 17 (addon `liv_delivery`) |
| API | FastAPI (Python 3.11) |
| Database | Postgres 16 |
| Cache / pubsub | Redis 7 |
| Driver app | Flutter (`liv_driver_app`) |
| Client app | Flutter (`liv_client_app`) |

## Documentation

- Docs home: `docs/`
- Changelog: `docs/CHANGELOG.md`
- Architecture: `docs/ARCHITECTURE.md`
- ADRs: `docs/adr/`
- Runbooks: `docs/runbooks/` (incl. `docs/runbooks/odoo-conf.md`)
- Flutter demos: `DEMO_FLUTTER_APPS.md`

## CI

| Workflow | Trigger | What it runs |
|----------|---------|-------------|
| `backend.yml` | push/PR on `backend-fastapi/**` | `pytest tests/test_health_status.py` (10 tests) |
| `flutter.yml` | push/PR on `liv_driver_app/**` or `liv_client_app/**` | `flutter pub get` + `flutter analyze` (both apps) |

## AI subagents (Cursor)

- **DocKeeper (documentation & changelog)**: `.cursor/agents/dockeeper.md`

## Apply changes (build & run)

```bash
docker compose up -d --build
```

Odoo DB connection is configured via `odoo.conf` (see `docs/runbooks/odoo-conf.md`) so Odoo CLI commands **do not need DB flags**.

## Run tests

```bash
# Backend unit tests (inside container)
docker compose exec fastapi python -m pytest -v tests/test_health_status.py

# Flutter static analysis
cd liv_driver_app && flutter analyze
cd liv_client_app && flutter analyze
```

---

## Backend health (FastAPI + Odoo)

### FastAPI endpoints: `/health` vs `/health/status`

- **`GET /health`**: simple liveness endpoint (no auth). Returns:
  - `{"ok": true}`
- **`GET /health/status`**: secured status endpoint (auth required).
  - **Auth**: token must match FastAPI `HEALTH_SECRET`
    - Header **either** `Authorization: Bearer <token>` **or** `X-Health-Token: <token>`
  - **Success (200)**: `ok=true` and includes:
    - `redis` (bool), `odoo` (bool), `ts` (ISO-8601 UTC string ending with `Z`)
  - **Failure (503)**: `ok=false` with `message` indicating which dependency is down
  - **Unauthorized (401)**: token missing/invalid (or `HEALTH_SECRET` not configured)

### Odoo configuration (System Parameters)

Configure these in Odoo: **Settings → Technical → Parameters → System Parameters**

- **`liv.fastapi_base_url`**: base URL used by Odoo cron (example: `http://fastapi:8000`)
- **`liv.health_secret`**: must match FastAPI `HEALTH_SECRET` (used as Bearer token for `/health/status`)

### Odoo UI: “LIV → Backend Status”

- Navigation: **LIV → Backend Status**
- Displays (read-only):
  - `status` (`ok` / `degraded` / `down` / `auth_error`)
  - `updated` (the `ts` returned by FastAPI `/health/status`)
  - `base_url`
  - `message`
- Note: values are read from system parameters at open time; **the secret is never displayed**.

### Scheduled action (cron)

Odoo schedules **“LIV: Check Backend Health”** every ~5 minutes; it calls:

- `GET <liv.fastapi_base_url>/health/status`
- Adds `Authorization: Bearer <liv.health_secret>` only when `liv.health_secret` is set

You can run it manually in **Settings → Technical → Automation → Scheduled Actions**.

### Runbook (quick triage)

- **status = `auth_error`**
  - Verify FastAPI `HEALTH_SECRET` is set (if empty/missing, `/health/status` will always return 401).
  - Ensure `liv.health_secret` matches `HEALTH_SECRET` exactly.
- **status = `down`**
  - If message is “Missing liv.fastapi_base_url”: set `liv.fastapi_base_url`.
  - If message starts with “Connection error: …”: base URL is unreachable from Odoo (wrong host/port/scheme, service down, networking).
- **status = `degraded`**
  - Check `/health/status` response to see which flag is failing (`redis=false` or `odoo=false`), then verify the corresponding service.

Then in Odoo:

1. **Install Sale** (if not already): Apps → search **Sale** → Install.
2. **Update Apps List**: Apps → ⋮ (top right) → **Update Apps List**, confirm.
3. **Upgrade module**: Search **LIV Delivery Tracking** → open the app card → **Upgrade** (v1.2 adds `sale` dependency and `sale_order_id` / sale order extensions for the demo flow).
4. **Configure Odoo system parameters** (Settings → Technical → Parameters → System Parameters):
   - `liv.fastapi_base_url`: use `http://fastapi:8000` when Odoo runs in this Docker Compose network
   - `liv.health_secret`: must match FastAPI `HEALTH_SECRET` (used for `/health/status`)
5. **Validate Backend Status UI**:
   - Open **LIV → Backend Status**
   - Expected: `status=ok`, `updated` is non-empty (ISO-8601 UTC, ends with `Z`), and `base_url` matches `liv.fastapi_base_url`

Or via CLI (DB config is implicit from `odoo.conf`, so no `-d`/DB flags; see `docs/runbooks/odoo-conf.md`):

```bash
docker compose exec odoo odoo -u liv_delivery --stop-after-init
```

If you had **Tracking Snapshots** from an old version (with `order_id`), delete them in Odoo before upgrading, or the schema change to `delivery_id` can cause upgrade errors.

---

## Testing steps

### 1. Create a delivery in Odoo and assign a driver

- Open **LIV → Deliveries** → **New**.
- Fill **Customer name**, **Address** (required). Optionally **Customer phone**, **Destination** (lat/lon).
- Set **Driver** to an existing user (e.g. admin or another user).
- Save, then click **Assign** (state becomes Assigned).

Note the **delivery ID** (e.g. `1`) from the form URL or the list view.

### 2. Get active mission via FastAPI (driver app)

```bash
# Replace 2 with the Odoo user ID of the driver (e.g. admin = often 2)
curl http://localhost:8000/drivers/2/active-mission
```

You should get `active_mission` with the delivery (or `null` if none in assigned/en_route/arrived for that driver).

### 3. Send tracking via WebSocket

**Hardening A.2**: The WS URL must include a valid `token` query parameter. Generate a token (e.g. with the same HMAC logic as the server: `base64(driver_id:delivery_id:timestamp:signature)` using `WS_SECRET`). Example with a pre-generated token:

```bash
npx wscat -c "ws://localhost:8000/ws/track?token=YOUR_GENERATED_TOKEN"
```

Then send JSON (replace `1` with your delivery ID, `2` with the driver's Odoo user ID). **`driver_id` is required** (Hardening A.1):

```json
{"delivery_id": 1, "driver_id": 2, "lat": 33.5731, "lon": -7.5898, "ts": "2026-02-15T15:00:00Z", "speed": 12.3, "heading": 90}
```

Send multiple messages; every ~60 seconds a snapshot is written to Odoo and the delivery’s last position is updated.

### 4. Verify in Odoo

- **LIV → Deliveries** → open the delivery: **Last known position** (last_lat, last_lon, last_ts) should update after the first 60s window.
- **Tracking Snapshots** tab: new lines should appear every 60 seconds per delivery while the WebSocket keeps sending.

### 5. Optional: change state via FastAPI

```bash
curl -X POST http://localhost:8000/deliveries/1/state -H "Content-Type: application/json" -d "{\"state\": \"en_route\"}"
```

### 6. Get delivery + last location from Redis

```bash
curl http://localhost:8000/deliveries/1
```

Returns delivery details and `last_location` / `redis_last` from Redis if the driver has sent at least one position.

---

## Demo flow: client order → mission → collect (curl)

Full flow matching the Flutter client and driver apps. **Prerequisite**: Odoo with **Sale** and **LIV Delivery Tracking** installed and upgraded (LIV addon v1.2+ with `sale` dependency).

**1. Place order (client)**

```bash
curl -X POST http://localhost:8000/client/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_name": "Jane Doe", "phone": "0612345678", "address": "123 Main St, Casablanca", "product_sku": "GAZ12", "qty": 1}'
```

Response: `{"sale_order_id": 1, "name": "S00042", "state": "draft", "amount_total": 100.0}`.

**2. Confirm order (backoffice)**

```bash
curl -X POST http://localhost:8000/backoffice/orders/1/confirm
```

Replace `1` with your `sale_order_id`. Response: `{"sale_order_id": 1, "name": "S00042", "state": "sale"}`.

**3. Create delivery mission (backoffice)**

```bash
curl -X POST http://localhost:8000/backoffice/orders/1/create-mission
```

Response: `{"delivery_id": 5, "sale_order_id": 1}`. Mission is created and assigned to driver 2 (demo default).

**4. Driver: active mission, state, tracking**

```bash
curl http://localhost:8000/drivers/2/active-mission
curl -X POST http://localhost:8000/deliveries/5/state -H "Content-Type: application/json" -d '{"state": "en_route"}'
# WS /ws/track?token=... with delivery_id=5, driver_id=2, lat, lon, ts (see Hardening A.2)
```

**5. Collect payment (COD) and mark delivered**

```bash
curl -X POST http://localhost:8000/deliveries/5/collect-payment \
  -H "Content-Type: application/json" \
  -d '{"method": "cash", "ref": "COD-001"}'
```

Response: `{"delivery_id": 5, "sale_order_id": 1, "payment_state": "paid", "delivery_state": "delivered"}`.

**Endpoints summary**

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/client/orders` | Create sale order (partner/product created or found) |
| POST | `/backoffice/orders/{id}/confirm` | Confirm sale order |
| POST | `/backoffice/orders/{id}/create-mission` | Create liv.delivery from order, link, assign |
| POST | `/deliveries/{id}/collect-payment` | Set payment on order + delivery state = delivered |

---

## Option A DoD – automated E2E (no Odoo UI)

To validate Option A without using the Odoo UI:

1. Enable the POC seed endpoint (for testing only):
   ```bash
   export POC_SEED_ENABLED=true
   ```
   Or add to `.env`:
   ```
   POC_SEED_ENABLED=true
   ```
   Then restart FastAPI (e.g. `docker compose up -d --build fastapi`).

2. Run the E2E script (from repo root). The script runs on your host and talks to FastAPI at `localhost:8000`; it needs `httpx`:
   ```bash
   pip install httpx   # if not already installed
   python scripts/test_e2e_option_a.py
   ```
   The script will: seed a delivery, check active-mission, send WS tracking for 70s, assert snapshots and last_*, then change state and verify. Exit code 0 = PASS, 1 = FAIL.

   Optional env vars: `BASE_URL=http://localhost:8000`, `WS_BASE_URL=ws://localhost:8000`.

---

## Hardening A.1 (security, robustness, back-pressure)

- **WS validation**: `/ws/track` requires `driver_id` in the JSON. The server checks that the delivery exists in Odoo, that `delivery.driver_id` matches `driver_id`, and that `delivery.state` is one of `assigned`, `en_route`, `arrived`. If any check fails, the server sends an error payload and closes the WebSocket with a clear reason.
- **Throttling**: At most one message every **10 seconds** per `(delivery_id, driver_id)`. Faster messages receive `{"error":"rate_limited","retry_after":<seconds>}`; Redis and Odoo are not updated for that message; the connection stays open.
- **Odoo resilience**: When Odoo is unavailable, the WS and Redis updates continue. Odoo writes (snapshot + last_*) are queued and retried in a background task with exponential backoff (capped at 30s). If the pending queue grows beyond 50 items, the oldest items are dropped and a warning is logged.
- **Config (env)**: `TRACK_RATE_LIMIT_SECONDS=10`, `ODOO_QUEUE_MAX=50`, `ODOO_BACKOFF_INITIAL=1`, `ODOO_BACKOFF_MAX=30`.

---

## Hardening A.2 – WS Auth & Redis Cache

Pre-production safety: prevent unauthorized tracking when Odoo is temporarily down.

- **WebSocket token auth**: `/ws/track` now requires a query parameter: `ws://.../ws/track?token=<token>`. Token is HMAC-based: `base64(driver_id:delivery_id:timestamp:signature)` with `signature = HMAC_SHA256(driver_id:delivery_id:timestamp, WS_SECRET)`. Token is valid only if the signature matches and the timestamp is not older than 5 minutes. If the token is missing or invalid, the server closes the WebSocket with code 1008 and logs `ws_rejected(reason="invalid_token")`.
- **Redis validation cache**: When validation against Odoo succeeds, the server stores `delivery:driver:<delivery_id> = driver_id` in Redis with TTL 600 seconds. When Odoo is unavailable, the server does **not** skip validation: it checks this Redis key. If the key matches the request’s `driver_id`, tracking is allowed; if the key is missing or does not match, the connection is rejected. When Odoo comes back, the first successful validation refreshes the cache.
- **Config (env)**: `WS_SECRET` (required; server fails to start if missing), `WS_TOKEN_MAX_AGE_SECONDS=300`, `DELIVERY_DRIVER_CACHE_TTL=600`.
- **E2E**: The script generates a valid token with the same HMAC logic, includes a negative test (invalid token → rejection), and keeps rate-limit and snapshot validation.

---

## Hardening A.3 – Production hygiene

- **WS secret rotation**: Optional env var `WS_SECRET_PREV` (previous secret). Token verification accepts signatures from either `WS_SECRET` (current) or `WS_SECRET_PREV`. Logs: `ws_token_verified(secret="current")` or `ws_token_verified(secret="prev")` (secrets are never logged). To rotate: deploy new secret as `WS_SECRET`, keep old as `WS_SECRET_PREV` for a grace period, then remove `WS_SECRET_PREV`.
- **Anti-replay / clock skew**: Tokens with timestamp older than `WS_TOKEN_MAX_AGE_SECONDS` are rejected (`token_expired`). Tokens with timestamp more than `WS_TOKEN_MAX_FUTURE_SKEW_SECONDS` (default 30) in the future are rejected (`token_in_future`). Rejection reasons in logs and WS close: `invalid_token_format`, `invalid_signature`, `token_expired`, `token_in_future`.
- **CORS**: Env var `ALLOWED_ORIGINS` (comma-separated). Default: `http://localhost:3000,http://localhost:5173`. FastAPI `CORSMiddleware`: `allow_origins` from env, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.
- **WebSocket Origin check**: For `/ws/track`, if the `Origin` header is **present** and not in `ALLOWED_ORIGINS`, the connection is rejected (1008, `origin_not_allowed`). If `Origin` is **missing** (e.g. mobile apps, wscat), the connection is allowed so non-browser clients keep working.

---

## Run tests (exact commands)

```bash
docker compose up -d --build fastapi
docker compose exec fastapi python -m pytest -v tests/test_health_status.py
python scripts/test_e2e_option_a.py
```

Ensure `POC_SEED_ENABLED=true` and `WS_SECRET=<your-secret>` in `.env` (or export them) so the E2E script can create a delivery and generate valid WS tokens. Optional: `WS_SECRET_PREV` to run the secret-rotation E2E step (b4).

---

## Flutter quick checks (client + driver)

Run `flutter analyze` and start the apps:

```bash
cd liv_client_app
flutter pub get
flutter analyze
flutter run
```

```bash
cd liv_driver_app
flutter pub get
flutter analyze
flutter run
```

### “Backend” badge (in both apps)

- The badge calls **`GET /health`** (no auth) with a 5s timeout.
- **Green/OK**: `Backend: OK (<latency>ms)`
- **Red/Down**: `Backend: Down — HTTP <code>` or an error type (e.g. timeout); tap the badge to refresh.
