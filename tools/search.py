import json

import requests
from langchain_core.tools import tool
from tavily import TavilyClient

from util.config import get_str

tavily_api_key = get_str("search.tavily_api_key")

@tool
def web_search(query: str) -> str:
    """ 网页数据搜索功能 """
    client = TavilyClient(tavily_api_key)
    response = client.search(
        query=f"{query}",
        search_depth="advanced"
    )
    return json.dumps(response, ensure_ascii=False)

@tool
def hot_search(query: str) -> str:
    """ 热搜功能 """
    try:
        req = requests.get(f"https://uapis.cn/api/v1/misc/hotboard?type={query}&limit=10")
        return req.json()
    except Exception as e:
        return "获取热搜信息时出错：" + str(e)
