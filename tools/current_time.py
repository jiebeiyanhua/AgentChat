from datetime import datetime

from langchain_core.tools import tool


@tool
def get_current_time() -> str:
    """返回当前时间。"""
    return "当前时间是：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S")