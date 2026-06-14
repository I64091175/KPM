#功能：統一處理台北時間顯示與儲存格式。
# utils/time_utils.py

from datetime import datetime
from config.settings import get_timezone


def get_now_taipei():
    """
    取得目前台北時間 datetime
    """
    tz = get_timezone()
    return datetime.now(tz)


def get_today_taipei():
    """
    取得台北日期（date）
    """
    return get_now_taipei().date()


def format_display_time(dt=None):
    """
    格式化為畫面顯示時間
    """
    if dt is None:
        dt = get_now_taipei()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_storage_time(dt=None):
    """
    格式化為寫入 Google Sheets 的時間格式
    """
    if dt is None:
        dt = get_now_taipei()
    return dt.strftime("%Y-%m-%d %H:%M:%S")