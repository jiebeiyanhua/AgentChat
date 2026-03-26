import json
import os
from typing import Any

import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None
HISTORY_CACHE_TTL = int(os.getenv("HISTORY_CACHE_TTL", "3600"))
SESSION_HEARTBEAT_TTL = int(os.getenv("SESSION_HEARTBEAT_TTL", "120"))

_redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
)


def get_redis_client() -> redis.Redis:
    return _redis_client


def get_history_cache_key(session_id: str) -> str:
    return f"chat:history:{session_id}"


def get_session_heartbeat_key(session_id: str) -> str:
    return f"chat:heartbeat:{session_id}"


def refresh_session_heartbeat(session_id: str) -> None:
    client = get_redis_client()
    client.set(get_session_heartbeat_key(session_id), "online", ex=SESSION_HEARTBEAT_TTL)


def cache_history_messages(session_id: str, messages: list[dict[str, Any]]) -> None:
    client = get_redis_client()
    key = get_history_cache_key(session_id)
    client.delete(key)
    if messages:
        client.rpush(key, *[json.dumps(message, ensure_ascii=False) for message in messages])
    client.expire(key, HISTORY_CACHE_TTL)


def append_history_message(session_id: str, message: dict[str, Any]) -> None:
    client = get_redis_client()
    key = get_history_cache_key(session_id)
    client.rpush(key, json.dumps(message, ensure_ascii=False))
    client.expire(key, HISTORY_CACHE_TTL)


def get_cached_history_messages(session_id: str) -> list[dict[str, Any]]:
    client = get_redis_client()
    key = get_history_cache_key(session_id)
    raw_messages = client.lrange(key, 0, -1)
    if not raw_messages:
        return []
    client.expire(key, HISTORY_CACHE_TTL)
    return [json.loads(item) for item in raw_messages]
