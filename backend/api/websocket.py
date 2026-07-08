import json
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from backend.config import settings

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/engagement/{engagement_id}")
async def engagement_stream(websocket: WebSocket, engagement_id: str):
    await websocket.accept()
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"engagement:{engagement_id}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await websocket.send_json(data)
                except (json.JSONDecodeError, WebSocketDisconnect):
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"engagement:{engagement_id}")
        await pubsub.close()
        await redis.aclose()
