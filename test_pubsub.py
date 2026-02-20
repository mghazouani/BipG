import asyncio
import json
import redis.asyncio as redis

async def test_pubsub():
    r = redis.from_url("redis://localhost:6379/0", decode_responses=True)
    pubsub = r.pubsub()
    
    # Subscribe to the channel
    await pubsub.subscribe("track:channel:1")
    print("Subscribed to track:channel:1, waiting for messages...")
    
    # Wait for messages
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                print(f"Received: {json.dumps(data, indent=2)}")
                break  # Just test one message
    finally:
        await pubsub.unsubscribe()
        await r.close()

if __name__ == "__main__":
    asyncio.run(test_pubsub())
