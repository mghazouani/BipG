import asyncio
import base64
import hmac
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Body, Depends, FastAPI, Header, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from pydantic import BaseModel

from .settings import (
    REDIS_URL,
    POC_SEED_ENABLED,
    TRACK_RATE_LIMIT_SECONDS,
    ODOO_QUEUE_MAX,
    ODOO_BACKOFF_INITIAL,
    ODOO_BACKOFF_MAX,
    WS_SECRET,
    WS_SECRET_PREV,
    WS_TOKEN_MAX_AGE_SECONDS,
    WS_TOKEN_MAX_FUTURE_SKEW_SECONDS,
    DELIVERY_DRIVER_CACHE_TTL,
    ALLOWED_ORIGINS,
    HEALTH_SECRET,
)
from .odoo_client import (
    login_uid,
    create_delivery_snapshot,
    update_delivery_last_position,
    get_active_mission_for_driver,
    set_delivery_state,
    read_delivery,
    read_partner,
    search_delivery_by_sale_order,
    create_delivery,
    write_delivery,
    read_delivery_tracks,
    find_or_create_partner,
    find_or_create_product,
    create_sale_order,
    read_sale_order,
    confirm_sale_order,
    search_pickings_for_sale_order,
    write_picking_user_id,
    ensure_liv_delivery_for_sale,
    find_outgoing_picking_for_sale,
    assign_driver_to_picking,
    create_mission_from_order,
    collect_payment,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

redis: Redis | None = None
odoo_queue: asyncio.Queue[dict[str, Any]] | None = None
_last_snapshot: dict[int, int] = {}
_rate_limit_last: dict[tuple[int, int], float] = {}
ACTIVE_STATES = ("assigned", "en_route", "arrived")
DELIVERY_DRIVER_KEY_PREFIX = "delivery:driver:"


def _verify_ws_token(token: str, driver_id: int, delivery_id: int) -> tuple[bool, str]:
    """Verify HMAC token. Returns (True, 'current'|'prev') or (False, reason). reason in: invalid_token_format, invalid_signature, token_expired, token_in_future."""
    try:
        raw = base64.b64decode(token, validate=True).decode("utf-8")
    except Exception:
        return (False, "invalid_token_format")
    parts = raw.split(":")
    if len(parts) != 4:
        return (False, "invalid_token_format")
    try:
        tid_driver, tid_delivery, ts_int, sig = int(parts[0]), int(parts[1]), int(parts[2]), parts[3]
    except ValueError:
        return (False, "invalid_token_format")
    if tid_driver != driver_id or tid_delivery != delivery_id:
        return (False, "invalid_signature")
    now = time.time()
    if ts_int > now + WS_TOKEN_MAX_FUTURE_SKEW_SECONDS:
        return (False, "token_in_future")
    if now - ts_int > WS_TOKEN_MAX_AGE_SECONDS:
        return (False, "token_expired")
    payload = f"{tid_driver}:{tid_delivery}:{ts_int}"
    for secret, label in [(WS_SECRET, "current"), (WS_SECRET_PREV, "prev")]:
        if not secret:
            continue
        expected = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, sig):
            return (True, label)
    return (False, "invalid_signature")


async def _odoo_queue_worker() -> None:
    """Background task: drain Odoo write queue with exponential backoff."""
    if odoo_queue is None:
        return
    backoff = ODOO_BACKOFF_INITIAL
    uid: int | None = None
    while True:
        try:
            item = await odoo_queue.get()
        except asyncio.CancelledError:
            break
        if uid is None:
            try:
                uid = await login_uid()
            except Exception as e:
                logger.warning("odoo_write_fail uid=%s", str(e)[:100])
                await odoo_queue.put(item)
                await asyncio.sleep(min(backoff, ODOO_BACKOFF_MAX))
                backoff = min(backoff * 2, ODOO_BACKOFF_MAX)
                continue
        try:
            await create_delivery_snapshot(
                uid, item["delivery_id"], item["driver_id"],
                item["lat"], item["lon"], item["ts"],
            )
            await update_delivery_last_position(
                uid, item["delivery_id"], item["lat"], item["lon"], item["ts"],
            )
            logger.info(
                "odoo_write_ok delivery_id=%s driver_id=%s",
                item["delivery_id"], item["driver_id"],
            )
            backoff = ODOO_BACKOFF_INITIAL
        except Exception as e:
            logger.warning(
                "odoo_write_fail delivery_id=%s exception=%s",
                item["delivery_id"], str(e)[:100],
            )
            await odoo_queue.put(item)
            await asyncio.sleep(min(backoff, ODOO_BACKOFF_MAX))
            backoff = min(backoff * 2, ODOO_BACKOFF_MAX)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis, odoo_queue
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    odoo_queue = asyncio.Queue()
    worker = asyncio.create_task(_odoo_queue_worker())
    yield
    worker.cancel()
    try:
        await worker
    except asyncio.CancelledError:
        pass
    if redis:
        await redis.close()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TrackMsg(BaseModel):
    delivery_id: int
    driver_id: int
    lat: float
    lon: float
    ts: str
    speed: float | None = None
    heading: float | None = None


class StateUpdate(BaseModel):
    state: str


class POCSeedDeliveryBody(BaseModel):
    customer_name: str
    customer_phone: str | None = None
    address: str
    lat: float | None = None
    lon: float | None = None
    driver_id: int
    state: str = "assigned"


class ClientOrderBody(BaseModel):
    customer_name: str
    phone: str
    address: str
    product_sku: str | None = None
    qty: int = 1


class CollectPaymentBody(BaseModel):
    amount: float | None = None
    method: str = "cash"
    ref: str | None = None


class CreateMissionBody(BaseModel):
    driver_user_id: int


def _driver_id_from_delivery(delivery: dict) -> int | None:
    """Odoo may return Many2one as id or [id, name]."""
    v = delivery.get("driver_id")
    if v is None:
        return None
    if isinstance(v, list):
        return v[0] if v else None
    return int(v)


def _validate_delivery_for_track(delivery: dict | None, driver_id: int) -> str | None:
    """Return None if valid, else error reason string."""
    if delivery is None:
        return "delivery_not_found"
    if _driver_id_from_delivery(delivery) != driver_id:
        return "driver_mismatch"
    if delivery.get("state") not in ACTIVE_STATES:
        return "invalid_state"
    return None


def _health_token_from_request(request: Request, x_health_token: str | None = Header(None, alias="X-Health-Token")) -> str | None:
    """Extract health token: Authorization Bearer or X-Health-Token header."""
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    if x_health_token is not None:
        return x_health_token.strip() or None
    return None


async def _verify_health_token(
    request: Request,
    x_health_token: str | None = Header(None, alias="X-Health-Token"),
) -> None:
    """Raise 401 if token missing or does not match HEALTH_SECRET."""
    token = _health_token_from_request(request, x_health_token)
    if not token or not HEALTH_SECRET:
        raise HTTPException(status_code=401, detail="Missing or invalid health token")
    if not hmac.compare_digest(token, HEALTH_SECRET):
        raise HTTPException(status_code=401, detail="Missing or invalid health token")


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/health/status", dependencies=[Depends(_verify_health_token)])
async def health_status():
    """Secured status: redis + odoo checks. Returns 503 when ok=false."""
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    redis_ok = False
    odoo_ok = False
    if redis:
        try:
            await redis.ping()
            redis_ok = True
        except Exception:
            pass
    try:
        await login_uid()
        odoo_ok = True
    except Exception:
        pass
    ok = redis_ok and odoo_ok
    payload: dict[str, Any] = {
        "ok": ok,
        "redis": redis_ok,
        "odoo": odoo_ok,
        "ts": ts,
    }
    if not ok:
        parts = []
        if not redis_ok:
            parts.append("redis down")
        if not odoo_ok:
            parts.append("odoo down")
        payload["message"] = "; ".join(parts)
        return JSONResponse(status_code=503, content=payload)
    return payload


@app.get("/drivers/{driver_id:int}/active-mission")
async def get_active_mission(driver_id: int):
    try:
        uid = await login_uid()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Odoo unavailable: {e}")
    mission = await get_active_mission_for_driver(uid, driver_id)
    if mission is None:
        return {"active_mission": None}
    return {"active_mission": mission}


@app.post("/deliveries/{delivery_id:int}/state")
async def update_delivery_state(delivery_id: int, body: StateUpdate):
    try:
        uid = await login_uid()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Odoo unavailable: {e}")
    try:
        await set_delivery_state(uid, delivery_id, body.state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"delivery_id": delivery_id, "state": body.state}


@app.get("/deliveries/{delivery_id:int}")
async def get_delivery(delivery_id: int):
    try:
        uid = await login_uid()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Odoo unavailable: {e}")
    delivery = await read_delivery(uid, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    redis_last = None
    if redis:
        raw = await redis.get(f"track:last:{delivery_id}")
        if raw:
            try:
                redis_last = json.loads(raw)
            except Exception:
                pass
    return {"delivery": delivery, "last_location": redis_last, "redis_last": redis_last}


@app.get("/deliveries/{delivery_id:int}/snapshots")
async def get_delivery_snapshots(delivery_id: int, limit: int = 5):
    try:
        uid = await login_uid()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Odoo unavailable: {e}")
    tracks = await read_delivery_tracks(uid, delivery_id, limit=limit)
    return {"delivery_id": delivery_id, "count": len(tracks), "snapshots": tracks}


def _extract_many2one_id(value: Any) -> int | None:
    """Odoo Many2one: can be id (int) or [id, name] or False."""
    if value is None or value is False:
        return None
    if isinstance(value, list):
        return value[0] if value else None
    return int(value)


def _is_odoo_unknown_field_error(exc: BaseException) -> bool:
    """True only if error explicitly mentions x_delivery_id and unknown/invalid field (ignore only that field)."""
    msg = str(exc).lower()
    if "x_delivery_id" not in msg:
        return False
    return (
        "unknown field" in msg
        or "invalid field" in msg
        or "field does not exist" in msg
    )


async def _read_sale_order_resilient(
    uid: int,
    order_id: int,
    fields_with_x: list[str],
    fields_without_x: list[str],
) -> dict:
    """Read sale.order; if x_delivery_id causes Odoo error, retry without it. Returns order dict."""
    try:
        order = await read_sale_order(uid, order_id, fields_with_x)
    except Exception as e:
        if not _is_odoo_unknown_field_error(e):
            raise
        order = await read_sale_order(uid, order_id, fields_without_x)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def _format_partner_address(partner: dict) -> str | None:
    """Build single address string from street, street2, zip, city (skip empty)."""
    parts = []
    for key in ("street", "street2"):
        v = (partner.get(key) or "").strip()
        if v:
            parts.append(v)
    zip_val = (partner.get("zip") or "").strip()
    city = (partner.get("city") or "").strip()
    if zip_val or city:
        parts.append(f"{zip_val} {city}".strip())
    if not parts:
        return partner.get("display_name") or None
    return ", ".join(parts)


@app.get("/client/orders/{sale_order_id:int}")
async def client_get_order(sale_order_id: int):
    """Get sale order by id for tracking. Returns ref, state, delivery_id, delivery_state, tracking_mode."""
    try:
        uid = await login_uid()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Odoo unavailable: {e}")
    order = await _read_sale_order_resilient(
        uid,
        sale_order_id,
        ["name", "state", "amount_total", "partner_id", "x_delivery_id"],
        ["name", "state", "amount_total", "partner_id"],
    )
    customer_name: str | None = None
    address: str | None = None
    partner_id = _extract_many2one_id(order.get("partner_id"))
    if partner_id:
        partner = await read_partner(uid, partner_id)
        if partner:
            customer_name = partner.get("name")
            address = _format_partner_address(partner)
    delivery_id: int | None = _extract_many2one_id(order.get("x_delivery_id"))
    delivery_state: str | None = None
    tracking_mode: str = "none"
    if delivery_id:
        tracking_mode = "x_delivery_id"
        try:
            delivery = await read_delivery(uid, delivery_id)
            if delivery:
                delivery_state = delivery.get("state")
        except Exception:
            delivery_state = None
    if delivery_id is None:
        fallback = await search_delivery_by_sale_order(uid, sale_order_id)
        if fallback:
            delivery_id = fallback.get("id")
            tracking_mode = "delivery_search"
            if delivery_id:
                try:
                    delivery = await read_delivery(uid, delivery_id)
                    if delivery:
                        delivery_state = delivery.get("state")
                except Exception:
                    pass
    return {
        "sale_order_id": sale_order_id,
        "ref": order.get("name", ""),
        "state": order.get("state", ""),
        "customer_name": customer_name,
        "address": address,
        "amount_total": order.get("amount_total"),
        "delivery_id": delivery_id,
        "delivery_state": delivery_state,
        "tracking_mode": tracking_mode,
    }


@app.post("/client/orders")
async def client_create_order(body: ClientOrderBody):
    try:
        uid = await login_uid()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Odoo unavailable: {e}")
    try:
        partner_id = await find_or_create_partner(
            uid, body.customer_name, body.phone, body.address
        )
        product_id = await find_or_create_product(uid, body.product_sku)
        order_id = await create_sale_order(uid, partner_id, product_id, qty=float(body.qty))
        order = await _read_sale_order_resilient(
            uid,
            order_id,
            ["name", "state", "amount_total", "x_delivery_id"],
            ["name", "state", "amount_total"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    delivery_id = _extract_many2one_id(order.get("x_delivery_id"))
    return {
        "sale_order_id": order_id,
        "ref": order.get("name", ""),
        "state": order.get("state", ""),
        "amount_total": order.get("amount_total", 0),
        "delivery_id": delivery_id,
    }


@app.post("/backoffice/orders/{sale_order_id:int}/confirm")
async def backoffice_confirm_order(sale_order_id: int):
    try:
        uid = await login_uid()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Odoo unavailable: {e}")
    try:
        order = await confirm_sale_order(uid, sale_order_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"sale_order_id": sale_order_id, "name": order.get("name", ""), "state": order.get("state", "")}


@app.post("/backoffice/orders/{sale_order_id:int}/create-mission")
async def backoffice_create_mission(sale_order_id: int, body: CreateMissionBody):
    """Create/assign mission from sale order: set Responsible (stock.picking.user_id) to driver;
    optionally sync liv.delivery and sale.order.x_delivery_id."""
    try:
        uid = await login_uid()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Odoo unavailable: {e}")
    order = await read_sale_order(uid, sale_order_id, ["name", "state"])
    if not order:
        raise HTTPException(status_code=404, detail="Sale order not found")
    if order.get("state") != "sale":
        try:
            await confirm_sale_order(uid, sale_order_id)
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))
    pickings = await search_pickings_for_sale_order(uid, sale_order_id)
    if not pickings:
        raise HTTPException(
            status_code=409,
            detail="No outgoing picking found for this order yet. Confirm the sale order and ensure a delivery order exists.",
        )
    picking = pickings[0]
    picking_id = picking["id"]
    picking_state = picking.get("state")
    try:
        await write_picking_user_id(uid, picking_id, body.driver_user_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    delivery_id: int | None = None
    delivery_state: str | None = None
    try:
        delivery_id, delivery_state = await ensure_liv_delivery_for_sale(
            uid, sale_order_id, body.driver_user_id
        )
    except Exception:
        pass
    return {
        "sale_order_id": sale_order_id,
        "sale_ref": order.get("name", ""),
        "picking_id": picking_id,
        "picking_state": picking_state,
        "driver_user_id": body.driver_user_id,
        "delivery_id": delivery_id,
        "delivery_state": delivery_state,
    }


@app.post("/deliveries/{delivery_id:int}/collect-payment")
async def delivery_collect_payment(delivery_id: int, body: CollectPaymentBody):
    try:
        uid = await login_uid()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Odoo unavailable: {e}")
    try:
        result = await collect_payment(
            uid, delivery_id, method=body.method, amount=body.amount, ref=body.ref
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return result


@app.post("/poc/seed/delivery")
async def poc_seed_delivery(body: POCSeedDeliveryBody):
    if not POC_SEED_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        uid = await login_uid()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Odoo unavailable: {e}")
    payload = {
        "customer_name": body.customer_name,
        "address": body.address,
        "driver_id": body.driver_id,
        "state": body.state,
    }
    if body.customer_phone is not None:
        payload["customer_phone"] = body.customer_phone
    if body.lat is not None:
        payload["lat"] = body.lat
    if body.lon is not None:
        payload["lon"] = body.lon
    try:
        delivery_id = await create_delivery(uid, payload)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    delivery = await read_delivery(uid, delivery_id)
    name = delivery.get("name", "LIV/????") if delivery else "LIV/????"
    return {"delivery_id": delivery_id, "name": name}


@app.websocket("/ws/track")
async def ws_track(ws: WebSocket):
    await ws.accept()
    if not redis:
        logger.info("ws_rejected reason=redis_not_available")
        await ws.close(code=1013, reason="Redis not available")
        return
    origin = next((v for k, v in ws.scope.get("headers", []) if k.lower() == b"origin"), None)
    if origin is not None:
        origin_str = origin.decode("utf-8", errors="replace").strip()
        if origin_str and origin_str not in ALLOWED_ORIGINS:
            logger.info("ws_rejected reason=origin_not_allowed origin=%s", origin_str)
            await ws.send_text(json.dumps({"error": "origin_not_allowed"}))
            await ws.close(code=1008, reason="origin_not_allowed")
            return
    token = ws.query_params.get("token")
    if not token:
        logger.info("ws_rejected reason=invalid_token")
        await ws.send_text(json.dumps({"error": "invalid_token"}))
        await ws.close(code=1008, reason="invalid_token")
        return
    token_validated = False
    uid_checked = False
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = TrackMsg(**json.loads(raw))
            except Exception as e:
                logger.info("ws_rejected reason=invalid_payload error=%s", str(e)[:80])
                await ws.send_text(json.dumps({"error": "invalid_payload", "detail": str(e)[:200]}))
                await ws.close(code=1008, reason="invalid_payload")
                return

            if not token_validated:
                ok, value = _verify_ws_token(token, msg.driver_id, msg.delivery_id)
                if not ok:
                    logger.info("ws_rejected reason=%s", value)
                    await ws.send_text(json.dumps({"error": value}))
                    await ws.close(code=1008, reason=value)
                    return
                logger.info("ws_token_verified secret=%s", value)
                token_validated = True

            delivery = None
            odoo_ok = False
            try:
                uid = await login_uid()
                delivery = await read_delivery(uid, msg.delivery_id)
                odoo_ok = True
            except Exception:
                pass
            reason = _validate_delivery_for_track(delivery, msg.driver_id)
            if odoo_ok:
                if reason is not None:
                    logger.info("ws_rejected delivery_id=%s driver_id=%s reason=%s", msg.delivery_id, msg.driver_id, reason)
                    await ws.send_text(json.dumps({"error": reason}))
                    await ws.close(code=1008, reason=reason)
                    return
                if redis:
                    await redis.set(
                        f"{DELIVERY_DRIVER_KEY_PREFIX}{msg.delivery_id}",
                        str(msg.driver_id),
                        ex=DELIVERY_DRIVER_CACHE_TTL,
                    )
            else:
                if not redis:
                    logger.info("ws_rejected delivery_id=%s driver_id=%s reason=odoo_down_no_redis", msg.delivery_id, msg.driver_id)
                    await ws.send_text(json.dumps({"error": "delivery_not_found"}))
                    await ws.close(code=1008, reason="delivery_not_found")
                    return
                cached = await redis.get(f"{DELIVERY_DRIVER_KEY_PREFIX}{msg.delivery_id}")
                if cached is None or int(cached) != msg.driver_id:
                    reason = "delivery_not_found" if cached is None else "driver_mismatch"
                    logger.info("ws_rejected delivery_id=%s driver_id=%s reason=%s (odoo_down)", msg.delivery_id, msg.driver_id, reason)
                    await ws.send_text(json.dumps({"error": reason}))
                    await ws.close(code=1008, reason=reason)
                    return
            if not uid_checked:
                logger.info("ws_connected delivery_id=%s driver_id=%s", msg.delivery_id, msg.driver_id)
                uid_checked = True

            now_mono = time.monotonic()
            key = (msg.delivery_id, msg.driver_id)
            last = _rate_limit_last.get(key, 0.0)
            elapsed = now_mono - last
            if elapsed < TRACK_RATE_LIMIT_SECONDS:
                retry_after = max(1, int(TRACK_RATE_LIMIT_SECONDS - elapsed + 0.999))
                logger.info("rate_limited delivery_id=%s driver_id=%s retry_after=%s", msg.delivery_id, msg.driver_id, retry_after)
                await ws.send_text(json.dumps({"error": "rate_limited", "retry_after": retry_after}))
                continue
            _rate_limit_last[key] = now_mono

            key_redis = f"track:last:{msg.delivery_id}"
            await redis.set(key_redis, json.dumps(msg.model_dump()), ex=3600)
            await redis.publish(f"track:channel:{msg.delivery_id}", json.dumps(msg.model_dump()))

            now_ts = int(time.time())
            last_snap = _last_snapshot.get(msg.delivery_id, 0)
            if now_ts - last_snap >= 60 and odoo_queue is not None:
                _last_snapshot[msg.delivery_id] = now_ts
                item = {
                    "delivery_id": msg.delivery_id,
                    "driver_id": msg.driver_id,
                    "lat": msg.lat,
                    "lon": msg.lon,
                    "ts": msg.ts,
                }
                if odoo_queue.qsize() >= ODOO_QUEUE_MAX:
                    try:
                        odoo_queue.get_nowait()
                        logger.warning("queue_drop count=1")
                    except asyncio.QueueEmpty:
                        pass
                await odoo_queue.put(item)

            await ws.send_text(json.dumps({"ack": True, "delivery_id": msg.delivery_id}))
    except WebSocketDisconnect:
        return

# ci smoke
