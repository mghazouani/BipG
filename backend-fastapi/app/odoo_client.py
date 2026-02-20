import httpx
from .settings import ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD

JSONRPC = f"{ODOO_URL}/jsonrpc"


async def _jsonrpc_call(service: str, method: str, args: list):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"service": service, "method": method, "args": args},
        "id": 1,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(JSONRPC, json=payload)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data["result"]


async def login_uid() -> int:
    return await _jsonrpc_call("common", "login", [ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD])


async def create_delivery_snapshot(
    uid: int, delivery_id: int, driver_id: int, lat: float, lon: float, ts: str
):
    """Create a liv.delivery.track record linked to liv.delivery."""
    return await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "liv.delivery.track",
            "create",
            [{
                "delivery_id": delivery_id,
                "driver_id": driver_id,
                "lat": lat,
                "lon": lon,
                "ts": ts,
            }],
        ],
    )


async def update_delivery_last_position(uid: int, delivery_id: int, lat: float, lon: float, ts: str):
    """Update liv.delivery last_lat, last_lon, last_ts."""
    return await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "liv.delivery",
            "write",
            [[delivery_id], {"last_lat": lat, "last_lon": lon, "last_ts": ts}],
        ],
    )


async def get_active_mission_for_driver(uid: int, driver_id: int) -> dict | None:
    """Return the first active delivery (state in assigned, en_route, arrived) for the given driver."""
    result = await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "liv.delivery",
            "search_read",
            [
                [["driver_id", "=", driver_id], ["state", "in", ["assigned", "en_route", "arrived"]]],
                ["id", "name", "customer_name", "customer_phone", "address", "lat", "lon", "state", "last_lat", "last_lon", "last_ts"],
            ],
            {"limit": 1, "order": "id desc"},
        ],
    )
    if not result:
        return None
    return result[0]


async def set_delivery_state(uid: int, delivery_id: int, state: str):
    """Set liv.delivery state (draft, assigned, en_route, arrived, delivered, cancelled)."""
    allowed = ("draft", "assigned", "en_route", "arrived", "delivered", "cancelled")
    if state not in allowed:
        raise ValueError(f"Invalid state: {state}")
    return await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "liv.delivery",
            "write",
            [[delivery_id], {"state": state}],
        ],
    )


async def read_delivery(uid: int, delivery_id: int) -> dict | None:
    """Return one liv.delivery by id or None if not found."""
    result = await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "liv.delivery",
            "read",
            [[delivery_id]],
            {"fields": ["id", "name", "customer_name", "customer_phone", "address", "lat", "lon", "driver_id", "state", "last_lat", "last_lon", "last_ts", "sale_order_id"]},
        ],
    )
    if not result:
        return None
    return result[0]


async def create_delivery(uid: int, payload: dict) -> int:
    """Create a liv.delivery in Odoo. Returns delivery_id (id). Name (LIV/000x) is assigned by sequence."""
    delivery_id = await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "liv.delivery",
            "create",
            [payload],
        ],
    )
    return delivery_id


async def write_delivery(uid: int, delivery_id: int, vals: dict):
    """Update liv.delivery fields (e.g. state)."""
    return await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "liv.delivery",
            "write",
            [[delivery_id], vals],
        ],
    )


async def search_delivery(uid: int, domain: list, limit: int = 1) -> list:
    """Search liv.delivery by domain, return list of ids."""
    return await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "liv.delivery",
            "search",
            [domain],
            {"limit": limit},
        ],
    )


def _is_odoo_model_or_field_missing(exc: BaseException) -> bool:
    """True if Odoo error indicates missing model (liv.delivery) or field (e.g. sale_order_id). Connectivity/auth errors return False so we re-raise."""
    msg = str(exc).lower()
    return (
        ("unknown field" in msg and ("sale_order_id" in msg or "liv.delivery" in msg))
        or ("field does not exist" in msg)
        or ("invalid field" in msg and "liv.delivery" in msg)
        or ("model" in msg and "not found" in msg)
    )


async def search_delivery_by_sale_order(uid: int, sale_order_id: int) -> dict | None:
    """Find liv.delivery by sale_order_id (fallback when x_delivery_id is missing).
    Returns first delivery dict with id, state or None if not found or on Odoo model/field missing.
    Connectivity/auth errors are re-raised."""
    try:
        result = await _jsonrpc_call(
            "object",
            "execute_kw",
            [
                ODOO_DB,
                uid,
                ODOO_PASSWORD,
                "liv.delivery",
                "search_read",
                [[["sale_order_id", "=", sale_order_id]]],
                {"fields": ["id", "state", "sale_order_id"], "limit": 1},
            ],
        )
        if not result:
            return None
        return result[0]
    except Exception as e:
        if _is_odoo_model_or_field_missing(e):
            return None
        raise


async def read_delivery_tracks(uid: int, delivery_id: int, limit: int = 5) -> list[dict]:
    """Return liv.delivery.track records for a delivery (last N by id desc)."""
    ids = await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "liv.delivery.track",
            "search",
            [[["delivery_id", "=", delivery_id]]],
            {"limit": limit, "order": "id desc"},
        ],
    )
    if not ids:
        return []
    return await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "liv.delivery.track",
            "read",
            [ids],
            {"fields": ["id", "delivery_id", "driver_id", "lat", "lon", "ts"]},
        ],
    )


# --- Client order & backoffice helpers ---


async def find_or_create_partner(uid: int, customer_name: str, phone: str, address: str) -> int:
    """Search res.partner by phone (mobile/phone) then by name; create if not found. Returns partner_id."""
    for field in ("mobile", "phone"):
        ids = await _jsonrpc_call(
            "object",
            "execute_kw",
            [
                ODOO_DB,
                uid,
                ODOO_PASSWORD,
                "res.partner",
                "search",
                [[[field, "=", phone]]],
                {"limit": 1},
            ],
        )
        if ids:
            return ids[0]
    ids = await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "res.partner",
            "search",
            [[["name", "=", customer_name]]],
            {"limit": 1},
        ],
    )
    if ids:
        return ids[0]
    partner_id = await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "res.partner",
            "create",
            [{"name": customer_name, "phone": phone or False, "street": address or False}],
        ],
    )
    return partner_id


async def find_or_create_product(uid: int, product_sku: str | None) -> int:
    """Find product by default_code (product.product); else create demo product. Returns product_id (product.product id)."""
    if product_sku:
        ids = await _jsonrpc_call(
            "object",
            "execute_kw",
            [
                ODOO_DB,
                uid,
                ODOO_PASSWORD,
                "product.product",
                "search",
                [[["default_code", "=", product_sku]]],
                {"limit": 1},
            ],
        )
        if ids:
            return ids[0]
    ids = await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "product.product",
            "search",
            [[]],
            {"limit": 1},
        ],
    )
    if ids:
        return ids[0]
    template_id = await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "product.template",
            "create",
            [
                {
                    "name": "Gas Delivery Demo",
                    "type": "service",
                    "list_price": 100.0,
                    "default_code": product_sku or "DEMO",
                }
            ],
        ],
    )
    variant_ids = await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "product.product",
            "search",
            [[["product_tmpl_id", "=", template_id]]],
            {"limit": 1},
        ],
    )
    return variant_ids[0]


async def create_sale_order(
    uid: int,
    partner_id: int,
    product_id: int,
    qty: float = 1.0,
) -> int:
    """Create sale.order in draft with one order line. Returns order id."""
    order_id = await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "sale.order",
            "create",
            [
                {
                    "partner_id": partner_id,
                    "order_line": [(0, 0, {"product_id": product_id, "product_uom_qty": qty})],
                }
            ],
        ],
    )
    return order_id


async def read_partner(uid: int, partner_id: int, fields: list | None = None) -> dict | None:
    """Read one res.partner by id. Returns dict or None."""
    if fields is None:
        fields = ["name", "street", "street2", "city", "zip", "display_name"]
    result = await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "res.partner",
            "read",
            [[partner_id]],
            {"fields": fields},
        ],
    )
    if not result:
        return None
    return result[0]


async def read_sale_order(uid: int, order_id: int, fields: list | None = None) -> dict | None:
    """Read one sale.order. Default fields include name, state, amount_total, partner_id, x_delivery_id."""
    if fields is None:
        fields = ["id", "name", "state", "amount_total", "partner_id", "partner_shipping_id", "x_delivery_id"]
    result = await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "sale.order",
            "read",
            [[order_id]],
            {"fields": fields},
        ],
    )
    if not result:
        return None
    return result[0]


async def confirm_sale_order(uid: int, order_id: int) -> dict:
    """Call action_confirm on sale.order. Idempotent if already confirmed. Returns updated order (name, state)."""
    await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "sale.order",
            "action_confirm",
            [[order_id]],
        ],
    )
    order = await read_sale_order(uid, order_id, ["name", "state"])
    return order or {"name": "", "state": ""}


def _picking_type_id_value(picking: dict) -> int | None:
    """Extract picking_type_id from picking (Many2one can be id or [id, name])."""
    v = picking.get("picking_type_id")
    if v is None:
        return None
    if isinstance(v, list):
        return v[0] if v else None
    return int(v)


async def search_pickings_for_sale_order(uid: int, sale_order_id: int) -> list[dict]:
    """Find stock.picking (Delivery Orders) for a sale order.
    Prefers origin == sale.order.name or sale_id == sale_order_id; filters by picking_type outgoing,
    state not in ('done','cancel'); returns list newest first (id desc)."""
    order = await read_sale_order(uid, sale_order_id, ["name", "state"])
    if not order:
        return []
    order_name = order.get("name") or ""
    fields = ["id", "name", "state", "picking_type_id", "location_id", "location_dest_id"]
    pickings: list[dict] = []
    try:
        result = await _jsonrpc_call(
            "object",
            "execute_kw",
            [
                ODOO_DB,
                uid,
                ODOO_PASSWORD,
                "stock.picking",
                "search_read",
                [[["sale_id", "=", sale_order_id]]],
                {"fields": fields, "limit": 50, "order": "id desc"},
            ],
        )
        pickings = result or []
    except Exception:
        pass
    if not pickings and order_name:
        try:
            result = await _jsonrpc_call(
                "object",
                "execute_kw",
                [
                    ODOO_DB,
                    uid,
                    ODOO_PASSWORD,
                    "stock.picking",
                    "search_read",
                    [[["origin", "=", order_name]]],
                    {"fields": fields, "limit": 50, "order": "id desc"},
                ],
            )
            pickings = result or []
        except Exception:
            pass
    skip_states = ("done", "cancel")
    pickings = [p for p in pickings if (p.get("state") or "") not in skip_states]
    try:
        type_ids = await _jsonrpc_call(
            "object",
            "execute_kw",
            [
                ODOO_DB,
                uid,
                ODOO_PASSWORD,
                "stock.picking.type",
                "search",
                [[["code", "=", "outgoing"]]],
                {"limit": 1},
            ],
        )
    except Exception:
        type_ids = []
    outgoing_type_id = type_ids[0] if type_ids else None
    if outgoing_type_id is not None:
        pickings = [p for p in pickings if _picking_type_id_value(p) == outgoing_type_id]
    return pickings


async def find_outgoing_picking_for_sale(uid: int, sale_order_id: int) -> dict | None:
    """First outgoing picking for sale order (newest by id)."""
    pickings = await search_pickings_for_sale_order(uid, sale_order_id)
    return pickings[0] if pickings else None


async def write_picking_user_id(uid: int, picking_id: int, driver_user_id: int) -> None:
    """Set stock.picking.user_id (Responsible) to driver_user_id. Standard Odoo field."""
    await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "stock.picking",
            "write",
            [[picking_id], {"user_id": driver_user_id}],
        ],
    )


async def ensure_liv_delivery_for_sale(
    uid: int, sale_order_id: int, driver_user_id: int
) -> tuple[int | None, str | None]:
    """Find or create liv.delivery for this sale order; set driver_id; link sale.order.x_delivery_id if field exists.
    Returns (delivery_id, delivery_state) or (None, None) only on model/field missing (e.g. liv.delivery not installed).
    Connectivity/auth/timeout errors are re-raised (502/503)."""
    try:
        existing = await _jsonrpc_call(
            "object",
            "execute_kw",
            [
                ODOO_DB,
                uid,
                ODOO_PASSWORD,
                "liv.delivery",
                "search_read",
                [[["sale_order_id", "=", sale_order_id]]],
                {"fields": ["id", "state"], "limit": 1},
            ],
        )
        if existing:
            delivery_id = existing[0]["id"]
            await _jsonrpc_call(
                "object",
                "execute_kw",
                [
                    ODOO_DB,
                    uid,
                    ODOO_PASSWORD,
                    "liv.delivery",
                    "write",
                    [[delivery_id], {"driver_id": driver_user_id, "state": "assigned"}],
                ],
            )
            state = existing[0].get("state") or "assigned"
            try:
                await _jsonrpc_call(
                    "object",
                    "execute_kw",
                    [
                        ODOO_DB,
                        uid,
                        ODOO_PASSWORD,
                        "sale.order",
                        "write",
                        [[sale_order_id], {"x_delivery_id": delivery_id}],
                    ],
                )
            except Exception as e:
                if not _is_odoo_unknown_field_write(e):
                    raise
            return (delivery_id, state)
        order = await read_sale_order(uid, sale_order_id, ["partner_id"])
        if not order:
            return (None, None)
        partner_id = order.get("partner_id")
        if isinstance(partner_id, list):
            partner_id = partner_id[0] if partner_id else None
        else:
            partner_id = int(partner_id) if partner_id else None
        if not partner_id:
            return (None, None)
        partner = await read_partner(uid, partner_id)
        customer_name = (partner or {}).get("name") or "Customer"
        address = (partner or {}).get("street") or (partner or {}).get("display_name") or ""
        if not address:
            address = str(partner_id)
        delivery_id = await _jsonrpc_call(
            "object",
            "execute_kw",
            [
                ODOO_DB,
                uid,
                ODOO_PASSWORD,
                "liv.delivery",
                "create",
                [
                    {
                        "sale_order_id": sale_order_id,
                        "customer_name": customer_name,
                        "address": address,
                        "driver_id": driver_user_id,
                        "state": "assigned",
                    }
                ],
            ],
        )
        try:
            await _jsonrpc_call(
                "object",
                "execute_kw",
                [
                    ODOO_DB,
                    uid,
                    ODOO_PASSWORD,
                    "sale.order",
                    "write",
                    [[sale_order_id], {"x_delivery_id": delivery_id}],
                ],
            )
        except Exception as e:
            if not _is_odoo_unknown_field_write(e):
                raise
        return (delivery_id, "assigned")
    except Exception as e:
        if _is_odoo_model_or_field_missing(e):
            return (None, None)
        raise


def _is_odoo_unknown_field_write(exc: BaseException) -> bool:
    """True if Odoo error indicates unknown/invalid field on write. Re-raise connectivity/auth."""
    msg = str(exc).lower()
    return "unknown field" in msg or "invalid field" in msg or "field does not exist" in msg


async def assign_driver_to_picking(
    uid: int,
    picking_id: int,
    driver_user_id: int | None = None,
    driver_partner_id: int | None = None,
) -> bool:
    """Assign driver to stock.picking via UI-created custom fields x_driver_user_id or x_driver_partner_id.
    Returns True if assignment succeeded. Returns False if field is missing (do not crash).
    Connectivity/auth errors are re-raised."""
    if driver_user_id is not None:
        try:
            await _jsonrpc_call(
                "object",
                "execute_kw",
                [
                    ODOO_DB,
                    uid,
                    ODOO_PASSWORD,
                    "stock.picking",
                    "write",
                    [[picking_id], {"x_driver_user_id": driver_user_id}],
                ],
            )
            return True
        except Exception as e:
            if _is_odoo_unknown_field_write(e):
                pass
            else:
                raise
    if driver_partner_id is not None:
        try:
            await _jsonrpc_call(
                "object",
                "execute_kw",
                [
                    ODOO_DB,
                    uid,
                    ODOO_PASSWORD,
                    "stock.picking",
                    "write",
                    [[picking_id], {"x_driver_partner_id": driver_partner_id}],
                ],
            )
            return True
        except Exception as e:
            if _is_odoo_unknown_field_write(e):
                pass
            else:
                raise
    return False


async def create_mission_from_order(uid: int, sale_order_id: int, default_driver_id: int = 2) -> int:
    """Validate order is confirmed (sale), create liv.delivery, link via x_delivery_id. Returns delivery_id."""
    order = await read_sale_order(uid, sale_order_id)
    if not order:
        raise ValueError("Sale order not found")
    if order.get("state") != "sale":
        raise ValueError("Order must be confirmed (state=sale) first")
    if order.get("x_delivery_id"):
        delivery_id = order["x_delivery_id"] if isinstance(order["x_delivery_id"], int) else order["x_delivery_id"][0]
        return delivery_id
    partner_id = order["partner_id"] if isinstance(order["partner_id"], int) else order["partner_id"][0]
    partner = await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "res.partner",
            "read",
            [[partner_id]],
            {"fields": ["name", "street", "city", "display_name"]},
        ],
    )
    partner_data = partner[0] if partner else {}
    address = partner_data.get("display_name") or partner_data.get("street") or partner_data.get("city") or ""
    if not address:
        address = str(partner_id)
    customer_name = partner_data.get("name") or "Customer"
    delivery_id = await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "liv.delivery",
            "create",
            [
                {
                    "customer_name": customer_name,
                    "address": address,
                    "sale_order_id": sale_order_id,
                    "state": "draft",
                    "driver_id": default_driver_id,
                }
            ],
        ],
    )
    await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "sale.order",
            "write",
            [[sale_order_id], {"x_delivery_id": delivery_id}],
        ],
    )
    await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "liv.delivery",
            "action_assign",
            [[delivery_id]],
        ],
    )
    return delivery_id


async def collect_payment(
    uid: int,
    delivery_id: int,
    method: str = "cash",
    amount: float | None = None,
    ref: str | None = None,
) -> dict:
    """Set delivery's sale_order x_payment_* and delivery state to delivered. Returns summary."""
    delivery = await read_delivery(uid, delivery_id)
    if not delivery:
        raise ValueError("Delivery not found")
    current = delivery.get("state", "")
    if current not in ("en_route", "arrived"):
        raise ValueError(
            f"Cannot mark as delivered from state '{current}' "
            f"(allowed: en_route, arrived)"
        )
    sale_order_id = delivery.get("sale_order_id")
    if isinstance(sale_order_id, list):
        sale_order_id = sale_order_id[0] if sale_order_id else None
    if not sale_order_id:
        raise ValueError("Delivery has no linked sale order")
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")  # Odoo datetime string
    await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "sale.order",
            "write",
            [
                [sale_order_id],
                {
                    "x_payment_state": "paid",
                    "x_payment_method": method,
                    "x_payment_ref": ref or "",
                    "x_payment_ts": now,
                },
            ],
        ],
    )
    await _jsonrpc_call(
        "object",
        "execute_kw",
        [
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "liv.delivery",
            "write",
            [[delivery_id], {"state": "delivered"}],
        ],
    )
    return {
        "delivery_id": delivery_id,
        "sale_order_id": sale_order_id,
        "payment_state": "paid",
        "delivery_state": "delivered",
    }
