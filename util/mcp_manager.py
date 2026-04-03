import asyncio
import hashlib
import json
import logging
import re
import threading
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any

import httpx
from langchain_core.tools import StructuredTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client
from pydantic import BaseModel, ConfigDict, Field, create_model

from util.config import get_bool, get_config

logger = logging.getLogger(__name__)


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _schema_description(schema: dict[str, Any], fallback: str) -> str:
    description = (schema.get("description") or fallback or "").strip()
    enum_values = schema.get("enum")
    if enum_values:
        description = f"{description} Allowed values: {', '.join(map(str, enum_values))}.".strip()
    return description


def _extract_json_type(schema: dict[str, Any]) -> tuple[Any, bool]:
    json_type = schema.get("type")
    if isinstance(json_type, list):
        allow_null = "null" in json_type
        candidates = [item for item in json_type if item != "null"]
        return (candidates[0] if candidates else "string"), allow_null
    return json_type or "string", False


def _build_annotation(schema: dict[str, Any], model_name: str) -> tuple[Any, bool]:
    json_type, allow_null = _extract_json_type(schema)
    if "anyOf" in schema or "oneOf" in schema or "allOf" in schema:
        return dict[str, Any], True

    if json_type == "string":
        return str, allow_null
    if json_type == "integer":
        return int, allow_null
    if json_type == "number":
        return float, allow_null
    if json_type == "boolean":
        return bool, allow_null
    if json_type == "array":
        items_schema = schema.get("items") or {}
        item_type, _ = _build_annotation(items_schema, f"{model_name}Item")
        return list[item_type], allow_null
    if json_type == "object":
        properties = schema.get("properties") or {}
        if not properties:
            return dict[str, Any], True
        return _create_args_model(model_name, schema), allow_null
    return Any, True


def _create_args_model(model_name: str, schema: dict[str, Any]) -> type[BaseModel]:
    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    fields: dict[str, tuple[Any, Any]] = {}

    if not properties:
        return create_model(
            model_name,
            __config__=ConfigDict(extra="allow", populate_by_name=True),
        )

    for field_name, field_schema in properties.items():
        if not field_name.isidentifier():
            logger.warning("Unsupported MCP argument name '%s'; falling back to free-form dict schema.", field_name)
            return create_model(
                model_name,
                payload=(dict[str, Any], Field(default_factory=dict, description="Raw MCP tool arguments.")),
                __config__=ConfigDict(extra="allow", populate_by_name=True),
            )

        annotation, allow_null = _build_annotation(field_schema, f"{model_name}_{field_name}".title())
        is_required = field_name in required
        if not is_required or allow_null:
            annotation = annotation | None

        default = ... if is_required else field_schema.get("default", None)
        description = _schema_description(field_schema, f"Argument '{field_name}' for the MCP tool.")
        fields[field_name] = (annotation, Field(default=default, description=description))

    return create_model(
        model_name,
        __config__=ConfigDict(extra="allow", populate_by_name=True),
        **fields,
    )


def _normalize_tool_name(server_name: str, tool_name: str) -> str:
    raw_name = f"mcp_{server_name}_{tool_name}"
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw_name)
    normalized = re.sub(r"_+", "_", normalized).strip("_-")
    digest = hashlib.sha1(raw_name.encode("utf-8")).hexdigest()[:10]
    if not normalized:
        return f"mcp_tool_{digest}"
    if len(normalized) < 8 or normalized == "mcp":
        return f"{normalized}_{digest}"
    return normalized


def _normalize_result(result: Any) -> str:
    blocks: list[str] = []

    structured = getattr(result, "structuredContent", None)
    if structured not in (None, {}):
        blocks.append(_json_dumps(structured))

    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            blocks.append(text)
            continue

        if hasattr(item, "model_dump"):
            blocks.append(_json_dumps(item.model_dump()))
            continue

        blocks.append(str(item))

    if not blocks:
        if hasattr(result, "model_dump"):
            return _json_dumps(result.model_dump())
        return str(result)

    return "\n".join(blocks)


@dataclass(slots=True)
class MCPServerConfig:
    name: str
    transport: str
    command: str | None = None
    args: list[str] = field(default_factory=list)
    url: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    enabled: bool = True


class _ManagedMCPServer:
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.exit_stack = AsyncExitStack()
        self.session: ClientSession | None = None
        self.tools: list[Any] = []
        self.status = "pending"
        self.error: str | None = None

    async def connect(self):
        transport = self.config.transport.strip().lower()
        if transport == "stdio":
            if not self.config.command:
                raise ValueError(f"MCP server '{self.config.name}' missing command for stdio transport.")

            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=self.config.env or None,
            )
            read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
        elif transport == "sse":
            if not self.config.url:
                raise ValueError(f"MCP server '{self.config.name}' missing url for sse transport.")
            read, write = await self.exit_stack.enter_async_context(
                sse_client(self.config.url, headers=self.config.headers or None)
            )
        elif transport in {"streamable_http", "streamable-http", "http"}:
            if not self.config.url:
                raise ValueError(f"MCP server '{self.config.name}' missing url for streamable_http transport.")
            http_client = None
            if self.config.headers:
                http_client = await self.exit_stack.enter_async_context(
                    httpx.AsyncClient(headers=self.config.headers)
                )
            read, write, _ = await self.exit_stack.enter_async_context(
                streamable_http_client(self.config.url, http_client=http_client)
            )
        else:
            raise ValueError(f"Unsupported MCP transport '{self.config.transport}' for server '{self.config.name}'.")

        self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        response = await self.session.list_tools()
        self.tools = list(response.tools)
        self.status = "connected"
        self.error = None

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        if self.session is None:
            raise RuntimeError(f"MCP server '{self.config.name}' is not connected.")
        result = await self.session.call_tool(tool_name, arguments=arguments)
        return _normalize_result(result)

    async def close(self):
        await self.exit_stack.aclose()
        self.status = "closed"


class MCPManager:
    def __init__(self):
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._servers: dict[str, _ManagedMCPServer] = {}
        self._tool_cache: list[Any] = []
        self._tool_metadata_cache: list[dict[str, Any]] = []
        self._started = False
        self._lock = threading.RLock()
        self.fail_fast = get_bool("mcp.fail_fast", default=False)

    def start(self):
        with self._lock:
            if self._started:
                return

            configs = self._load_configs()
            if not configs:
                logger.info("MCP is not configured; skipping MCP startup.")
                self._started = True
                return

            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._run_loop, name="mcp-manager-loop", daemon=True)
            self._thread.start()
            try:
                self._run_sync(self._connect_servers(configs))
            except Exception:
                self._run_sync(self._close_servers())
                self._loop.call_soon_threadsafe(self._loop.stop)
                self._thread.join(timeout=5)
                self._servers.clear()
                self._tool_cache = []
                self._tool_metadata_cache = []
                self._loop = None
                self._thread = None
                raise
            self._started = True

    def stop(self):
        with self._lock:
            if not self._started:
                return

            if self._loop is not None and self._thread is not None:
                self._run_sync(self._close_servers())
                self._loop.call_soon_threadsafe(self._loop.stop)
                self._thread.join(timeout=5)

            self._servers.clear()
            self._tool_cache = []
            self._tool_metadata_cache = []
            self._loop = None
            self._thread = None
            self._started = False

    def reload(self):
        with self._lock:
            if self._started:
                self.stop()
            self.start()

    def get_langchain_tools(self) -> list[Any]:
        return list(self._tool_cache)

    def get_tool_metadata(self) -> list[dict[str, Any]]:
        return list(self._tool_metadata_cache)

    def get_server_statuses(self) -> list[dict[str, Any]]:
        result = []
        for server in self._servers.values():
            result.append(
                {
                    "name": server.config.name,
                    "transport": server.config.transport,
                    "status": server.status,
                    "tool_count": len(server.tools),
                    "tools": [tool.name for tool in server.tools],
                    "error": server.error,
                    "url": server.config.url,
                    "command": server.config.command,
                    "args": server.config.args,
                }
            )
        return result

    def call_tool_sync(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> str:
        return self._run_sync(self._call_tool(server_name, tool_name, arguments))

    async def _call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> str:
        server = self._servers.get(server_name)
        if server is None:
            raise RuntimeError(f"MCP server '{server_name}' is not available.")
        return await server.call_tool(tool_name, arguments)

    async def _connect_servers(self, configs: list[MCPServerConfig]):
        self._servers = {}
        self._tool_cache = []
        self._tool_metadata_cache = []

        for config in configs:
            server = _ManagedMCPServer(config)
            self._servers[config.name] = server
            try:
                await server.connect()
                logger.info(
                    "Connected MCP server '%s' via %s with %d tools.",
                    config.name,
                    config.transport,
                    len(server.tools),
                )
            except Exception as exc:
                server.status = "error"
                server.error = str(exc)
                logger.exception("Failed to connect MCP server '%s': %s", config.name, exc)
                if self.fail_fast:
                    raise
                continue

        self._tool_cache, self._tool_metadata_cache = self._build_langchain_tools()

    async def _close_servers(self):
        for server in self._servers.values():
            try:
                await server.close()
            except Exception:
                logger.exception("Failed to close MCP server '%s'.", server.config.name)

    def _build_langchain_tools(self) -> tuple[list[Any], list[dict[str, Any]]]:
        tool_list = []
        tool_metadata = []
        for server_name, server in self._servers.items():
            if server.status != "connected":
                continue

            for tool in server.tools:
                input_schema = getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}}
                args_model = _create_args_model(
                    f"MCP_{server_name}_{tool.name}".replace("-", "_").replace(".", "_"),
                    input_schema,
                )
                langchain_name = _normalize_tool_name(server_name, tool.name)
                description = (getattr(tool, "description", None) or "").strip()
                if description:
                    description = f"[MCP:{server_name}] {description}"
                else:
                    description = f"[MCP:{server_name}] Call MCP tool '{tool.name}'."

                def _make_func(current_server: str, current_tool: str):
                    def _run(**kwargs):
                        payload = kwargs.get("payload")
                        arguments = payload if isinstance(payload, dict) else kwargs
                        logger.info("Calling MCP tool %s/%s", current_server, current_tool)
                        return self.call_tool_sync(current_server, current_tool, arguments)

                    return _run

                tool_list.append(
                    StructuredTool.from_function(
                        func=_make_func(server_name, tool.name),
                        name=langchain_name,
                        description=description,
                        args_schema=args_model,
                    )
                )
                tool_metadata.append(
                    {
                        "server_name": server_name,
                        "tool_name": tool.name,
                        "langchain_name": langchain_name,
                        "description": (getattr(tool, "description", None) or "").strip(),
                        "transport": server.config.transport,
                    }
                )

        return tool_list, tool_metadata

    def _run_loop(self):
        assert self._loop is not None
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_sync(self, coro):
        if self._loop is None:
            raise RuntimeError("MCP manager loop is not running.")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def _load_configs(self) -> list[MCPServerConfig]:
        data = get_config("mcp.servers", [])
        return self.parse_server_configs(data)

    def parse_server_configs(self, data: Any) -> list[MCPServerConfig]:
        if not data:
            return []
        if not isinstance(data, list):
            raise ValueError("mcp.servers must be a JSON array.")

        configs: list[MCPServerConfig] = []
        seen_names: set[str] = set()

        for item in data:
            if not isinstance(item, dict):
                raise ValueError("Each MCP server config must be an object.")

            enabled = item.get("enabled", True)
            if isinstance(enabled, str):
                enabled = _parse_bool(enabled, default=True)
            if not enabled:
                continue

            name = str(item.get("name") or "").strip()
            transport = str(item.get("transport") or "stdio").strip()
            if not name:
                raise ValueError("Each MCP server config must include a name.")
            if name in seen_names:
                raise ValueError(f"Duplicate MCP server name '{name}'.")
            seen_names.add(name)

            args = item.get("args") or []
            if not isinstance(args, list):
                raise ValueError(f"MCP server '{name}' args must be a JSON array.")

            configs.append(
                MCPServerConfig(
                    name=name,
                    transport=transport,
                    command=item.get("command"),
                    args=[str(arg) for arg in args],
                    url=item.get("url"),
                    env={str(key): str(value) for key, value in (item.get("env") or {}).items()},
                    headers={str(key): str(value) for key, value in (item.get("headers") or {}).items()},
                    enabled=bool(enabled),
                )
            )

        return configs


mcp_manager = MCPManager()
