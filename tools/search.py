import requests
from langchain_core.tools import tool


@tool
def web_search(query: str) -> str:
    """ 网页数据搜索功能 """
    return "未实现"

@tool
def hot_search(query: str) -> str:
    """ 热搜功能 """
    try:
        req = requests.get(f"https://uapis.cn/api/v1/misc/hotboard?type={query}&limit=10")
        return req.json()
    except Exception as e:
        return "获取热搜信息时出错：" + str(e)
