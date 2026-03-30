from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool
from util.config import get_str

APP_TIMEZONE = get_str("time.app_timezone", "Asia/Shanghai")

def _get_app_timezone() -> ZoneInfo:
    return ZoneInfo(APP_TIMEZONE)

@tool
def get_current_time() -> str:
    """返回当前时间。"""
    return "当前时间是：" + datetime.now(_get_app_timezone()).strftime("%Y-%m-%d %H:%M:%S")
