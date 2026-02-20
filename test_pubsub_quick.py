#!/usr/bin/env python3
"""Subscribe to track:channel:99, send one WS message, check we receive it."""
import asyncio
import json
import sys
try:
    import websockets
    import redis.asyncio as redis
except ImportError:
    print("pip install websockets redis"); sys.exit(1)

async def run():
    r = redis.from_url("redis://localhost:6379/0", decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("track:channel:99")
    received = asyncio.Event()
    payloads = []

    async def listener():
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                payloads.append(json.loads(msg["data"]))
                received.set()
                break

    async def send_ws():
        await asyncio.sleep(0.5)
        uri = "ws://localhost:8000/ws/track"
        msg = {"delivery_id": 99, "lat": 33.58, "lon": -7.60, "ts": "2026-02-15T12:01:00Z"}
        async with websockets.connect(uri, close_timeout=2) as ws:
            await ws.send(json.dumps(msg))
            await ws.recv()

    await asyncio.gather(listener(), send_ws())
    ok = asyncio.wait_for(received.wait(), timeout=3)
    try:
        await ok
    except asyncio.TimeoutError:
        await pubsub.unsubscribe()
        await r.close()
        print("PUBSUB_FAIL: no message received")
        return 1
    await pubsub.unsubscribe()
    await r.close()
    if payloads and payloads[0].get("delivery_id") == 99:
        print("PUBSUB_OK: received event on track:channel:99")
        return 0
    print("PUBSUB_FAIL:", payloads)
    return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
