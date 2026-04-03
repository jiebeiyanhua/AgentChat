from langchain_core.tools import tool

from util.mcp_manager import mcp_manager


@tool
def get_mcp_server_list() -> str:
    """查询当前可用的 MCP 服务列表。"""
    servers = mcp_manager.get_server_statuses()
    if not servers:
        return "当前没有可用的 MCP 服务。"

    lines = ["当前可用的 MCP 服务列表："]
    for item in servers:
        lines.append(
            f"- name={item['name']} | transport={item['transport']} | status={item['status']} | tool_count={item['tool_count']}"
        )
    return "\n".join(lines)


@tool
def get_mcp_tools_by_server(server_name: str) -> str:
    """查询指定 MCP 服务下的工具列表。在调用具体 MCP 工具前应先使用此工具。"""
    name = (server_name or "").strip().lower()
    if not name:
        return "请提供 MCP 服务名称。"

    metadata = [item for item in mcp_manager.get_tool_metadata() if item["server_name"].lower() == name]
    if not metadata:
        return f"未找到服务 {server_name} 对应的 MCP 工具列表。"

    lines = [f"MCP 服务 {server_name} 的工具列表："]
    for item in metadata:
        description = item.get("description") or "-"
        lines.append(
            f"- tool={item['tool_name']} | langchain_name={item['langchain_name']} | description={description}"
        )
    return "\n".join(lines)
