from tools.current_time import get_current_time
from tools.history_search import search_early_history
from tools.knowledge_definitions import get_knowledge_definitions
from tools.prmpot import retrieve_profile
from tools.safe_shell import safe_shell
from tools.search import hot_search, web_search
from tools.tool_executor import ToolExecutor
from tools.weather import get_weather
from util.mcp_manager import mcp_manager


def tools_list():
    tool_executor = ToolExecutor()
    tool_executor.registerTool(
        "get_knowledge_definitions",
        "列出所有知识库定义及其 source_key 和描述。在调用 retrieve_profile 之前应先调用此工具，以便选择最相关的知识库。",
        get_knowledge_definitions,
    )
    tool_executor.registerTool(
        "retrieve_profile",
        "在调用 get_knowledge_definitions 之后，基于选定的 source_key 检索指定的数据库知识库。",
        retrieve_profile,
    )
    tool_executor.registerTool("search_early_history", "检索当前会话下更早的历史消息。", search_early_history)
    tool_executor.registerTool("get_current_time", "获取当前本地时间。", get_current_time)
    tool_executor.registerTool("web_search", "在网络上搜索最新信息或未知信息。", web_search)
    tool_executor.registerTool("get_weather", "获取指定城市的天气信息。", get_weather)
    tool_executor.registerTool("hot_search", "获取支持平台上的热门话题,支持中英文搜索，以下是支持的平台："
    "bilibili(哔哩哔哩),acfun(A站),weibo(微博热搜),zhihu(知乎热榜),douyin(抖音),hupu(虎扑),baidu(百度热搜),"
    "thepaper(澎湃新闻),toutiao(今日头条),qq-news(腾讯新闻),sina-news(新浪新闻),netease-news(网易新闻),"
    "juejin(掘金),lol(英雄联盟),starrail(星穹铁道)", hot_search)
    tool_executor.registerTool(
        "safe_shell",
        "在工作区内运行只读的终端检查命令。禁止破坏性或修改文件的命令。请优先使用精炼、聚焦的查询命令，以减少查询次数。",
        safe_shell,
    )
    for tool in mcp_manager.get_langchain_tools():
        tool_executor.registerTool(tool.name, tool.description, tool)
    return tool_executor

