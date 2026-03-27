from tools.current_time import get_current_time
from tools.history_search import search_early_history
from tools.knowledge_definitions import get_knowledge_definitions
from tools.prmpot import retrieve_profile
from tools.safe_shell import safe_shell
from tools.search import hot_search, web_search
from tools.tool_executor import ToolExecutor
from tools.weather import get_weather


def tools_list():
    tool_executor = ToolExecutor()
    tool_executor.registerTool(
        "get_knowledge_definitions",
        "List all knowledge base definitions with source_key and descriptions. Always call this before retrieve_profile so you can choose the most relevant knowledge base.",
        get_knowledge_definitions,
    )
    tool_executor.registerTool(
        "retrieve_profile",
        "Search a specific database-backed knowledge base by source_key after calling get_knowledge_definitions.",
        retrieve_profile,
    )
    tool_executor.registerTool("search_early_history", "Search earlier history under the current session.", search_early_history)
    tool_executor.registerTool("get_current_time", "Get the current local time.", get_current_time)
    tool_executor.registerTool("web_search", "Search the web for recent or unknown information.", web_search)
    tool_executor.registerTool("get_weather", "Get weather information for a specified city.", get_weather)
    tool_executor.registerTool("hot_search", "Get trending topics from supported platforms.", hot_search)
    tool_executor.registerTool(
        "safe_shell",
        "Run read-only terminal inspection commands inside the workspace. Destructive or file-modifying commands are blocked.",
        safe_shell,
    )
    return tool_executor

