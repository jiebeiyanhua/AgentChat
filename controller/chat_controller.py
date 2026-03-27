import asyncio
import json
from contextlib import suppress

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessage, HumanMessage

from util.DbChatMessageHistory import DbChatMessageHistory
from util.agent import AgentLLM
from util.db_models import ChatMessage, SessionLocal
from util.knowledge_base import list_knowledge_definitions
from util.redis_client import refresh_session_heartbeat
from util.time_utils import format_datetime

router = APIRouter()
llm_client = AgentLLM()


def serialize_db_history_message(message: ChatMessage) -> dict:
    payload = json.loads(message.content)
    message_type = payload.get("type")
    role = "system"
    metadata = {}
    if message.additional_metadata:
        try:
            metadata = json.loads(message.additional_metadata)
        except json.JSONDecodeError:
            metadata = {}

    if message_type == "human":
        role = "user"
    elif message_type == "ai":
        role = "assistant"
    elif metadata.get("display_mode") in {"assistant_action", "assistant_note"}:
        role = "assistant"

    return {
        "id": message.id,
        "role": role,
        "content": payload.get("data", {}).get("content", ""),
        "timestamp": format_datetime(message.timestamp),
        "hide_timestamp": bool(metadata.get("hide_timestamp")),
        "message_kind": metadata.get("message_kind", "chat"),
    }


def _stringify_value(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _compact_text(value, limit: int = 180) -> str:
    text = " ".join(_stringify_value(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _extract_action_field(action, field: str):
    if isinstance(action, dict):
        return action.get(field)
    return getattr(action, field, None)


def _extract_action_preface(action) -> str | None:
    message_log = _extract_action_field(action, "message_log")
    if isinstance(message_log, list):
        parts = []
        for item in message_log:
            content = getattr(item, "content", None)
            if isinstance(content, str):
                normalized = " ".join(content.split()).strip()
                if normalized:
                    parts.append(normalized)
        if parts:
            return "\n".join(parts)

    raw_log = _extract_action_field(action, "log")
    if isinstance(raw_log, str) and raw_log.strip():
        marker = "responded:"
        if marker in raw_log:
            responded = raw_log.split(marker, 1)[1].strip()
            if responded:
                return responded
    return None


def _find_knowledge_definition(source_key: str | None) -> dict | None:
    if not source_key:
        return None

    for item in list_knowledge_definitions():
        if item.source_key == source_key:
            return {
                "source_key": item.source_key,
                "source_name": item.source_name,
                "source_type": item.source_type,
                "file_path": item.file_path,
                "description": item.description,
            }
    return None


def build_action_preface_message(action) -> dict | None:
    preface = _extract_action_preface(action)
    if not preface:
        return None

    return {
        "content": preface,
        "metadata": {
            "display_mode": "assistant_note",
            "hide_timestamp": False,
            "message_kind": "chat",
        },
    }


def build_action_message(action) -> dict:
    tool_name = _extract_action_field(action, "tool") or "unknown_tool"
    tool_input = _extract_action_field(action, "tool_input")
    normalized_input = tool_input if isinstance(tool_input, dict) else {"input": tool_input}

    if tool_name == "get_knowledge_definitions":
        content = "\n".join(
            [
                "知识库选择",
                f"方法：{tool_name}",
                "动作：读取当前可用的知识库定义列表，准备选择最合适的知识来源。",
            ]
        )
        return {
            "content": content,
            "metadata": {
                "display_mode": "assistant_action",
                "hide_timestamp": True,
                "message_kind": "knowledge",
            },
        }

    if tool_name == "retrieve_profile":
        source_key = _stringify_value(normalized_input.get("source_key"))
        query_text = _compact_text(normalized_input.get("query"))
        definition = _find_knowledge_definition(source_key)
        source_label = definition["source_name"] if definition else source_key
        file_path = definition["file_path"] if definition else None

        lines = [
            "知识库检索",
            f"方法：{tool_name}",
            "方式：向量相似度检索",
            f"知识库：{source_label}",
            f"source_key：{source_key}",
            f"检索问题：{query_text}",
        ]
        if file_path:
            lines.append(f"知识文件：{file_path}")

        return {
            "content": "\n".join(lines),
            "metadata": {
                "display_mode": "assistant_action",
                "hide_timestamp": True,
                "message_kind": "knowledge",
            },
        }

    argument_lines = [
        f"{key}：{_compact_text(value)}"
        for key, value in normalized_input.items()
        if value not in (None, "")
    ]
    content_lines = ["工具调用", f"方法：{tool_name}"]
    if argument_lines:
        content_lines.append("参数：" + "；".join(argument_lines))
    else:
        content_lines.append("参数：无")

    return {
        "content": "\n".join(content_lines),
        "metadata": {
            "display_mode": "assistant_action",
            "hide_timestamp": True,
            "message_kind": "tool",
        },
    }


async def stream_agent_events(input_text: str, session_id: str):
    history = DbChatMessageHistory(session_id=session_id)
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict] = asyncio.Queue()
    full_response = ""
    history.add_message(HumanMessage(content=input_text))

    def run_think():
        try:
            print("--- Calling LLM ---")
            for chunk in llm_client.think(input_text, session_id):
                if "output" in chunk:
                    output = chunk["output"]
                    print(f"AI: {output}", end="", flush=True)
                    loop.call_soon_threadsafe(queue.put_nowait, {"type": "chunk", "content": output})
                elif "actions" in chunk:
                    print(f"[Tool action] {chunk['actions']}")
                    actions = chunk["actions"]
                    if not isinstance(actions, list):
                        actions = [actions]
                    for action in actions:
                        action_preface = build_action_preface_message(action)
                        if action_preface is not None:
                            history.add_system_message(
                                action_preface["content"],
                                metadata=action_preface["metadata"],
                            )
                            loop.call_soon_threadsafe(
                                queue.put_nowait,
                                {
                                    "type": "assistant_note",
                                    "content": action_preface["content"],
                                    "hide_timestamp": action_preface["metadata"]["hide_timestamp"],
                                    "message_kind": action_preface["metadata"]["message_kind"],
                                },
                            )

                        action_message = build_action_message(action)
                        history.add_system_message(
                            action_message["content"],
                            metadata=action_message["metadata"],
                        )
                        loop.call_soon_threadsafe(
                            queue.put_nowait,
                            {
                                "type": "action",
                                "content": action_message["content"],
                                "hide_timestamp": action_message["metadata"]["hide_timestamp"],
                                "message_kind": action_message["metadata"]["message_kind"],
                            },
                        )

            loop.call_soon_threadsafe(queue.put_nowait, {"type": "done"})
        except Exception as exc:
            print(f"Error: {exc}")
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

            if event_type == "assistant_note":
                yield event
                continue

            if event_type == "error":
                yield event
                break

            if event_type == "done":
                if full_response:
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
    db = SessionLocal()
    try:
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.timestamp.asc())
            .all()
        )
    finally:
        db.close()

    return {
        "session_id": session_id,
        "messages": [serialize_db_history_message(message) for message in messages],
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
                    await websocket.send_json(
                        {
                            "type": "action",
                            "content": event["content"],
                            "hide_timestamp": event.get("hide_timestamp", True),
                            "message_kind": event.get("message_kind", "tool"),
                        }
                    )
                elif event["type"] == "assistant_note":
                    await websocket.send_json(
                        {
                            "type": "assistant_note",
                            "content": event["content"],
                            "hide_timestamp": event.get("hide_timestamp", False),
                            "message_kind": event.get("message_kind", "chat"),
                        }
                    )
                elif event["type"] == "error":
                    await websocket.send_json({"type": "error", "message": event["content"]})
                elif event["type"] == "done":
                    await websocket.send_json({"type": "done", "message": "[DONE]"})
    except WebSocketDisconnect:
        print("WebSocket disconnected")
