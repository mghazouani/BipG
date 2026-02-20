#!/usr/bin/env python3
"""Quick WS test: connect, send one message with delivery_id, check ack."""
import asyncio
import json
import sys
try:
    import websockets
except ImportError:
    print("pip install websockets"); sys.exit(1)

async def main():
    uri = "ws://localhost:8000/ws/track"
    msg = {"delivery_id": 99, "lat": 33.57, "lon": -7.59, "ts": "2026-02-15T12:00:00Z"}
    try:
        async with websockets.connect(uri, close_timeout=2) as ws:
            await ws.send(json.dumps(msg))
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(raw)
            if data.get("ack") is True and data.get("delivery_id") == 99:
                print("WS_OK: ack received with delivery_id=99")
                return 0
            print("WS_FAIL:", data)
            return 1
    except Exception as e:
        print("WS_ERROR:", e)
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
