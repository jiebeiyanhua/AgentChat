import asyncio
import logging
from contextlib import suppress
from datetime import datetime

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessage, HumanMessage

from util.DbChatMessageHistory import DbChatMessageHistory
from util.agent import AgentLLM
from util.redis_client import refresh_session_heartbeat

router = APIRouter()
llm_client = AgentLLM()
logger = logging.getLogger(__name__)


def serialize_history_message(message):
    timestamp = None
    if getattr(message, "metadata", None):
        timestamp = message.metadata.get("timestamp")

    role = "system"
    if message.type == "human":
        role = "user"
    elif message.type == "ai":
        role = "assistant"

    return {
        "id": getattr(message, "id", None),
        "role": role,
        "content": message.content,
        "timestamp": timestamp or datetime.utcnow().isoformat(),
    }


async def stream_agent_events(input_text: str, session_id: str):
    history = DbChatMessageHistory(session_id=session_id)
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict] = asyncio.Queue()
    full_response = ""

    def run_think():
        try:
            logger.info("Calling LLM for session_id=%s.", session_id)
            for chunk in llm_client.think(input_text, session_id):
                if "output" in chunk:
                    output = chunk["output"]
                    logger.debug("Streaming chunk received, length=%d.", len(output))
                    loop.call_soon_threadsafe(queue.put_nowait, {"type": "chunk", "content": output})
                elif "actions" in chunk:
                    logger.info("Tool action triggered: %s", chunk["actions"])
                    loop.call_soon_threadsafe(queue.put_nowait, {"type": "action", "content": str(chunk["actions"])})

            loop.call_soon_threadsafe(queue.put_nowait, {"type": "done"})
        except Exception as exc:
            logger.exception("Error while streaming LLM events for session_id=%s: %s", session_id, exc)
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "content": str(exc)})

    worker = asyncio.create_task(asyncio.to_thread(run_think))

    try:
        while True:
            event = await queue.get()
            event_type = event["type"]

            if event_type == "chunk":
                full_response += event["content"]
                yield event
                continue

            if event_type == "action":
                yield event
                continue

            if event_type == "error":
                yield event
                break

            if event_type == "done":
                if full_response:
                    history.add_message(HumanMessage(content=input_text))
                    history.add_message(AIMessage(content=full_response))
                yield event
                break
    finally:
        if not worker.done():
            worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker


@router.get("/agent-history")
async def get_agent_history(session_id: str = Query(..., min_length=1)):
    history = DbChatMessageHistory(session_id=session_id)
    return {
        "session_id": session_id,
        "messages": [serialize_history_message(message) for message in history.messages],
    }


@router.websocket("/ws/agent-talk")
async def websocket_talk(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            payload = await websocket.receive_json()
            message_type = (payload.get("type") or "").strip()
            session_id = (payload.get("session_id") or "").strip()

            if message_type == "heartbeat":
                if session_id:
                    refresh_session_heartbeat(session_id)
                await websocket.send_json({"type": "heartbeat_ack", "session_id": session_id})
                continue

            input_text = (payload.get("input_text") or "").strip()

            if not input_text or not session_id:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "input_text and session_id are required",
                    }
                )
                continue

            refresh_session_heartbeat(session_id)
            async for event in stream_agent_events(input_text, session_id):
                if event["type"] == "chunk":
                    await websocket.send_json({"type": "chunk", "content": event["content"]})
                elif event["type"] == "action":
                    await websocket.send_json({"type": "action", "content": event["content"]})
                elif event["type"] == "error":
                    await websocket.send_json({"type": "error", "message": event["content"]})
                elif event["type"] == "done":
                    await websocket.send_json({"type": "done", "message": "[DONE]"})
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected.")
