import logging
from typing import Any

logger = logging.getLogger(__name__)


class ToolExecutor:
    """一个工具执行器，负责管理和执行工具。"""

    def __init__(self):
        self.tools: dict[str, dict[str, Any]] = {}

    def registerTool(self, name: str, description: str, func: callable, category: str = "tool"):
        """向工具箱中注册一个新工具。"""
        if name in self.tools:
            logger.warning("Tool '%s' already exists and will be overwritten.", name)
        self.tools[name] = {
            "description": description,
            "func": func,
            "category": category,
        }

    def getTool(self, name: str) -> callable:
        """根据名称获取一个工具的执行函数。"""
        return self.tools.get(name, {}).get("func")

    def getAvailableTools(self, category: str | None = None) -> str:
        """获取所有可用工具的格式化描述字符串。"""
        items = self.tools.items()
        if category is not None:
            items = [(name, info) for name, info in items if info.get("category") == category]

        return "\n".join(
            [
                f"- {name}: {info['description']}"
                for name, info in items
            ]
        )

    def getToolsList(self) -> list:
        """获取所有可用工具的列表。"""
        return [info["func"] for info in self.tools.values()]
