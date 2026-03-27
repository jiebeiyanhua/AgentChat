import os
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Shanghai")

def _get_app_timezone() -> ZoneInfo:
    return ZoneInfo(APP_TIMEZONE)

@tool
def get_current_time() -> str:
    """返回当前时间。"""
    return "当前时间是：" + datetime.now(_get_app_timezone()).strftime("%Y-%m-%d %H:%M:%S")