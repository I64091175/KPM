import pandas as pd
import streamlit as st

from config.constants import WORKSHEET_AI_ARCHIVE
from services.data_service import (
    fetch_sheet,
    append_row,
    filter_by_patient_id,
    safe_sort_by_datetime,
)
from utils.time_utils import format_storage_time


ARCHIVE_REQUIRED_COLUMNS = ["病歷號", "日期", "判定結果", "AI衛教建議"]


def normalize_patient_id(patient_id):
    """
    標準化病歷號
    """
    if patient_id is None:
        return ""
    return str(patient_id).strip()


def build_archive_row(patient_id, ai_text, summary_text):
    """
    建立一筆 archive 資料列
    """
    patient_id = normalize_patient_id(patient_id)

    row = pd.DataFrame([
        {
            "病歷號": patient_id,
            "日期": format_storage_time(),
            "判定結果": summary_text if summary_text else "",
            "AI衛教建議": ai_text if ai_text else "",
        }
    ])

    return row


def fetch_ai_history(conn, patient_id):
    """
    讀取某病人的所有 AI 衛教歷史
    """
    patient_id = normalize_patient_id(patient_id)

    if not patient_id:
        return pd.DataFrame()

    df_archive = fetch_sheet(conn, WORKSHEET_AI_ARCHIVE, ttl=10)

    if df_archive is None or df_archive.empty:
        return pd.DataFrame()

    filtered_df = filter_by_patient_id(df_archive, patient_id, patient_id_column="病歷號")
    filtered_df = safe_sort_by_datetime(filtered_df, datetime_column="日期")

    return filtered_df


def fetch_latest_ai_advice(conn, patient_id):
    """
    讀取某病人最新一筆 AI 衛教紀錄
    回傳 dict 或 None
    """
    history_df = fetch_ai_history(conn, patient_id)

    if history_df is None or history_df.empty:
        return None

    latest_row = history_df.iloc[0].to_dict()
    return latest_row


def save_ai_advice(conn, patient_id, ai_text, summary_text):
    """
    儲存 AI 衛教紀錄到 AI_Education_Archive
    """
    patient_id = normalize_patient_id(patient_id)

    if not patient_id:
        st.error("❌ 病歷號不可為空，無法儲存 AI 衛教。")
        return False

    row_df = build_archive_row(patient_id, ai_text, summary_text)
    success = append_row(conn, WORKSHEET_AI_ARCHIVE, row_df)

    if success:
        st.success("✅ AI 衛教建議已成功儲存至雲端。")

    return success


def get_latest_ai_text(conn, patient_id):
    """
    只取最新 AI文字，方便 UI 直接顯示
    """
    latest = fetch_latest_ai_advice(conn, patient_id)
    if not latest:
        return None

    return latest.get("AI衛教建議", None)


def get_latest_summary_text(conn, patient_id):
    """
    只取最新判定摘要
    """
    latest = fetch_latest_ai_advice(conn, patient_id)
    if not latest:
        return None

    return latest.get("判定結果", None)
