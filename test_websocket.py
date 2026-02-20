import asyncio
import json
import websockets

async def test_websocket():
    uri = "ws://localhost:8000/ws/track"
    message = {
        "order_id": 1,
        "lat": 33.5731,
        "lon": -7.5898,
        "ts": "2026-02-15T15:00:00Z",
        "speed": 12.3,
        "heading": 90
    }
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            print(f"Sending: {json.dumps(message, indent=2)}")
            
            await websocket.send(json.dumps(message))
            response = await websocket.recv()
            print(f"Received: {response}")
            
            # Send a few more messages to test the 60s snapshot logic
            for i in range(2):
                await asyncio.sleep(1)
                message["lat"] += 0.001
                await websocket.send(json.dumps(message))
                response = await websocket.recv()
                print(f"Received: {response}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
