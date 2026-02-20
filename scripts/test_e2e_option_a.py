#!/usr/bin/env python3
"""
E2E test for Option A DoD: seed delivery, active-mission, WS tracking, snapshots, state change.
Hardening A.2: WS requires ?token= (HMAC); invalid token rejected; rate limit and snapshots validated.
Uses only httpx (already in requirements) and stdlib. No websockets dep: minimal WS client inline.
Run: POC_SEED_ENABLED=true WS_SECRET=yoursecret python scripts/test_e2e_option_a.py
"""
from __future__ import annotations

import asyncio
import base64
import hmac
import hashlib
import json
import os
import struct
import sys
import time
import urllib.parse

try:
    import httpx
except ImportError:
    print("FAIL: httpx required. pip install httpx")
    sys.exit(1)

def _load_dotenv() -> None:
    """Load .env from repo root (stdlib only, no python-dotenv)."""
    for path in (os.path.join(os.path.dirname(__file__), "..", ".env"), ".env"):
        p = os.path.abspath(path)
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            break


_load_dotenv()

BASE = os.getenv("BASE_URL", "http://localhost:8000")
WS_BASE = os.getenv("WS_BASE_URL", "ws://localhost:8000")
DRIVER_ID = 2
WS_SECRET = os.getenv("WS_SECRET", "").encode("utf-8")
WS_SECRET_PREV = os.getenv("WS_SECRET_PREV", "").encode("utf-8")
WS_TOKEN_MAX_FUTURE_SKEW_SECONDS = int(os.getenv("WS_TOKEN_MAX_FUTURE_SKEW_SECONDS", "30"))


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def pass_(msg: str) -> None:
    print(f"PASS: {msg}")


def make_ws_token(driver_id: int, delivery_id: int, secret: bytes, timestamp: int | None = None) -> str:
    """HMAC token: base64(driver_id:delivery_id:timestamp:signature)."""
    if not secret:
        raise ValueError("WS_SECRET env var is required for E2E (WS auth).")
    ts = int(time.time()) if timestamp is None else timestamp
    payload = f"{driver_id}:{delivery_id}:{ts}"
    sig = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    raw = f"{payload}:{sig}"
    return base64.b64encode(raw.encode("utf-8")).decode("ascii")


async def ws_send_receive_once(ws_url: str, payload: dict) -> dict:
    """Minimal WebSocket client (stdlib only): connect, send one text frame, read one, return parsed JSON."""
    parsed = urllib.parse.urlparse(ws_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "wss" else 8000)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    reader, writer = await asyncio.open_connection(host, port)
    try:
        key = base64.b64encode(os.urandom(16)).decode().strip()
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        writer.write(req.encode())
        await writer.drain()

        line = b""
        while b"\r\n\r\n" not in line:
            line += await reader.read(1024)
        if b"101" not in line and b"101 Switching" not in line:
            raise RuntimeError(f"Expected 101 Upgrade, got: {line[:200]}")

        text = json.dumps(payload)
        text_bytes = text.encode("utf-8")
        mask = os.urandom(4)
        payload_len = len(text_bytes)
        frame = bytearray()
        frame.append(0x81)
        frame.append(0x80 | (payload_len & 0x7F))
        frame.extend(mask)
        for i, b in enumerate(text_bytes):
            frame.append(b ^ mask[i % 4])
        writer.write(bytes(frame))
        await writer.drain()

        h = await reader.read(2)
        if len(h) < 2:
            raise RuntimeError("WS read timeout")
        opcode = h[0] & 0x0F
        length = h[1] & 0x7F
        if length == 126:
            ext = await reader.read(2)
            length = struct.unpack(">H", ext)[0]
        elif length == 127:
            ext = await reader.read(8)
            length = struct.unpack(">Q", ext)[0]
        body = await reader.read(length)
        if opcode != 0x01:
            raise RuntimeError(f"Unexpected opcode {opcode}")
        return json.loads(body.decode("utf-8"))
    finally:
        writer.close()
        await writer.wait_closed()


async def run() -> None:
    if not WS_SECRET:
        fail("WS_SECRET env var is required for E2E (Hardening A.2 WS auth). Set it and re-run.")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # a) POST /poc/seed/delivery
        print("(a) POST /poc/seed/delivery ...")
        r = await client.post(
            f"{BASE}/poc/seed/delivery",
            json={
                "customer_name": "Test Customer",
                "customer_phone": "0600000000",
                "address": "Casablanca",
                "lat": 33.5731,
                "lon": -7.5898,
                "driver_id": DRIVER_ID,
                "state": "assigned",
            },
        )
        if r.status_code == 404:
            fail("POST /poc/seed/delivery returned 404. Set POC_SEED_ENABLED=true and restart FastAPI.")
        if r.status_code != 200:
            fail(f"POST /poc/seed/delivery: {r.status_code} {r.text}")
        data = r.json()
        delivery_id = data.get("delivery_id")
        name = data.get("name", "")
        if not delivery_id or not name.startswith("LIV/"):
            fail(f"Expected delivery_id and name LIV/xxxx, got {data}")
        pass_(f"Created delivery {delivery_id} {name}")

        # b) GET /drivers/2/active-mission
        print("(b) GET /drivers/2/active-mission ...")
        r = await client.get(f"{BASE}/drivers/{DRIVER_ID}/active-mission")
        if r.status_code != 200:
            fail(f"GET active-mission: {r.status_code}")
        mission = r.json().get("active_mission")
        if not mission:
            fail("active_mission is null")
        if mission.get("id") != delivery_id:
            fail(f"active_mission id {mission.get('id')} != {delivery_id}")
        pass_(f"active_mission returns delivery_id={delivery_id}")

        # b2) Invalid token: connect with bad token, expect rejection
        print("(b2) WS invalid token -> expect rejection ...")
        ws_url_bad = f"{WS_BASE}/ws/track?token=invalid_token_value"
        ts = "2026-02-15T12:00:00Z"
        msg_bad = {"delivery_id": delivery_id, "driver_id": DRIVER_ID, "lat": 33.57, "lon": -7.59, "ts": ts}
        try:
            resp = await ws_send_receive_once(ws_url_bad, msg_bad)
        except Exception as e:
            fail(f"WS with invalid token: expected JSON error response, got: {e}")
        invalid_errors = ("invalid_token", "invalid_token_format", "invalid_signature", "token_expired", "token_in_future")
        if resp.get("error") not in invalid_errors:
            fail(f"Expected error in {invalid_errors}, got {resp}")
        pass_("invalid token rejected")

        # b3) Future timestamp token -> expect token_in_future rejection
        print("(b3) WS token with future timestamp -> expect rejection ...")
        future_ts = int(time.time()) + WS_TOKEN_MAX_FUTURE_SKEW_SECONDS + 10
        token_future = make_ws_token(DRIVER_ID, delivery_id, WS_SECRET, timestamp=future_ts)
        ws_url_future = f"{WS_BASE}/ws/track?token={token_future}"
        try:
            resp_future = await ws_send_receive_once(ws_url_future, msg_bad)
        except Exception as e:
            fail(f"WS with future token: expected JSON response, got: {e}")
        if resp_future.get("error") != "token_in_future":
            fail(f"Expected error=token_in_future, got {resp_future}")
        pass_("future timestamp token rejected")

        # b4) Secret rotation: if WS_SECRET_PREV set, token signed with prev must work
        if WS_SECRET_PREV:
            print("(b4) WS token signed with WS_SECRET_PREV -> expect ack ...")
            token_prev = make_ws_token(DRIVER_ID, delivery_id, WS_SECRET_PREV)
            ws_url_prev = f"{WS_BASE}/ws/track?token={token_prev}"
            ack_prev = await ws_send_receive_once(ws_url_prev, msg_bad)
            if not ack_prev.get("ack") or ack_prev.get("delivery_id") != delivery_id:
                fail(f"Token with WS_SECRET_PREV should ack, got {ack_prev}")
            pass_("WS_SECRET_PREV token accepted")
            await asyncio.sleep(11)
        else:
            print("(b4) WS_SECRET_PREV not set -> skip secret rotation test")

        # c0) Rate limit: 2 messages back-to-back, second must get rate_limited
        print("(c0) WS rate limit: 2 messages back-to-back, expect second rate_limited ...")
        token = make_ws_token(DRIVER_ID, delivery_id, WS_SECRET)
        ws_url = f"{WS_BASE}/ws/track?token={token}"
        ts = "2026-02-15T12:00:00Z"
        msg1 = {"delivery_id": delivery_id, "driver_id": DRIVER_ID, "lat": 33.57, "lon": -7.59, "ts": ts}
        ack1 = await ws_send_receive_once(ws_url, msg1)
        if not ack1.get("ack"):
            fail(f"First message should ack, got {ack1}")
        msg2 = {"delivery_id": delivery_id, "driver_id": DRIVER_ID, "lat": 33.571, "lon": -7.59, "ts": ts}
        ack2 = await ws_send_receive_once(ws_url, msg2)
        if ack2.get("error") != "rate_limited" or "retry_after" not in ack2:
            fail(f"Second message should be rate_limited, got {ack2}")
        pass_("rate_limited received on back-to-back send")
        await asyncio.sleep(11)

        # c) WS tracking: valid token + driver_id in payload; every 10s for 70s
        print("(c) WS /ws/track send every 10s for 70s (with driver_id) ...")
        token = make_ws_token(DRIVER_ID, delivery_id, WS_SECRET)
        ws_url = f"{WS_BASE}/ws/track?token={token}"
        ts = "2026-02-15T12:00:00Z"
        lat, lon = 33.5731, -7.5898

        def ws_msg(i: int):
            return {
                "delivery_id": delivery_id,
                "driver_id": DRIVER_ID,
                "lat": lat + i * 0.001,
                "lon": lon,
                "ts": ts,
                "speed": 10.0,
            }

        for i in range(8):
            msg = ws_msg(i)
            try:
                ack = await ws_send_receive_once(ws_url, msg)
            except Exception as e:
                fail(f"WS send/receive: {e}")
            if not ack.get("ack") or ack.get("delivery_id") != delivery_id:
                fail(f"WS ack unexpected: {ack}")
            if i < 7:
                await asyncio.sleep(10)
        pass_("WS tracking sent for 70s")

        # d) GET /deliveries/{id} -> last_* set in Odoo
        print("(d) GET /deliveries/{id} last_* and redis_last ...")
        r = await client.get(f"{BASE}/deliveries/{delivery_id}")
        if r.status_code != 200:
            fail(f"GET delivery: {r.status_code}")
        body = r.json()
        delivery = body.get("delivery") or {}
        redis_last = body.get("redis_last")
        if not redis_last:
            fail("redis_last is null (expected last position from Redis)")
        if delivery.get("last_lat") is None and delivery.get("last_lon") is None:
            fail("delivery.last_lat/last_lon not set in Odoo after 60s tracking")
        pass_("delivery has last_* and redis_last")

        # e) GET /deliveries/{id}/snapshots -> at least one
        print("(e) GET /deliveries/{id}/snapshots ...")
        r = await client.get(f"{BASE}/deliveries/{delivery_id}/snapshots", params={"limit": 5})
        if r.status_code != 200:
            fail(f"GET snapshots: {r.status_code}")
        snap = r.json()
        count = snap.get("count", 0)
        if count < 1:
            fail(f"Expected at least 1 snapshot, got count={count}")
        pass_(f"snapshots count={count}")

        # f) POST state -> en_route, verify via GET
        print("(f) POST state en_route and verify ...")
        r = await client.post(f"{BASE}/deliveries/{delivery_id}/state", json={"state": "en_route"})
        if r.status_code != 200:
            fail(f"POST state: {r.status_code}")
        r = await client.get(f"{BASE}/deliveries/{delivery_id}")
        if r.status_code != 200:
            fail(f"GET delivery after state: {r.status_code}")
        state = (r.json().get("delivery") or {}).get("state")
        if state != "en_route":
            fail(f"Expected state en_route, got {state}")
        pass_("state changed to en_route and verified")

    print("\n--- All steps PASSED (Option A DoD E2E) ---")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(run())
