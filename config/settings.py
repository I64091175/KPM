#功能：管理 Gemini API、Google Sheets 連線、Taipei 時區。
# config/settings.py

from datetime import timezone, timedelta
import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection


def get_timezone():
    """
    回傳台北時區（UTC+8）
    """
    return timezone(timedelta(hours=8))


def get_google_api_key():
    """
    從 Streamlit secrets 取得 Gemini API Key
    若未設定，回傳 None
    """
    try:
        return st.secrets.get("GOOGLE_API_KEY", None)
    except Exception:
        return None


def configure_gemini():
    """
    初始化 Gemini
    回傳:
        (enabled: bool, message: str)
    """
    api_key = get_google_api_key()

    if not api_key:
        return False, "未找到 GOOGLE_API_KEY，AI 功能將停用。"

    try:
        genai.configure(api_key=api_key)
        return True, "Gemini 初始化成功。"
    except Exception as e:
        return False, f"Gemini 初始化失敗：{str(e)}"


def is_ai_enabled():
    """
    檢查 AI 是否可用
    """
    api_key = get_google_api_key()
    return bool(api_key)


def get_gsheets_connection():
    """
    建立 Google Sheets 連線
    """
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn
    except Exception as e:
        st.error(f"Google Sheets 連線失敗：{str(e)}")
        return None