from tools.current_time import get_current_time
from tools.prmpot import retrieve_profile
from tools.search import web_search, hot_search
from tools.tool_executor import ToolExecutor
from tools.weather import get_weather


def tools_list():
    toolExecutor = ToolExecutor()
    toolExecutor.registerTool("retrieve_profile","用于了解用户信息、自身身份或行为准则", retrieve_profile)
    toolExecutor.registerTool("get_current_time","获取当前时间", get_current_time)
    toolExecutor.registerTool("web_search","一个网页搜索引擎,当你需要回答关于时事、事实以及在你的知识库中找不到的信息时使用", web_search)
    toolExecutor.registerTool("get_weather","获取用户当前的天气情况，需要先获取用户当前的地区位置（可能存放在用户信息里）,按城市名称查询，支持中文（北京）和英文（Tokyo）", get_weather)
    toolExecutor.registerTool("hot_search","获取weibo（新浪微博热搜）,douyin（抖音热榜）,kuaishou（快手热榜）,baidu（百度热搜）, thepaper（澎湃新闻热榜）, toutiao（今日头条热榜）某一家的热搜数据,按提供的名称查询，只支持英文（weibo）", hot_search)
    return toolExecutor