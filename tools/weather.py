import requests
from langchain_core.tools import tool


@tool
def get_weather(query: str) -> str:
    """获取当前的天气情况"""
    try:
        req = requests.get(f"https://uapis.cn/api/v1/misc/weather?city={query}")
        return req.json()
    except Exception as e:
        return "获取天气信息时出错：" + str(e)
