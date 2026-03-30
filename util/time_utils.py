from datetime import datetime
from zoneinfo import ZoneInfo

from util.config import get_str

DISPLAY_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
APP_TIMEZONE = get_str("time.app_timezone", "Asia/Shanghai")


def _get_app_timezone() -> ZoneInfo:
    return ZoneInfo(APP_TIMEZONE)


def now_local() -> datetime:
    # Persist the intended local wall-clock time instead of relying on container timezone.
    return datetime.now(_get_app_timezone()).replace(tzinfo=None)


def format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(_get_app_timezone()).strftime(DISPLAY_TIME_FORMAT)
    return value.strftime(DISPLAY_TIME_FORMAT)
