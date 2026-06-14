#這個檔案負責：Google Sheets 讀資料、寫資料、快取時間、欄位驗證、錯誤處理。
# fetch_data_with_buffer()、fetch_data_no_cache() 與 Google Sheets 連線後的操作。
# services/data_service.py


import pandas as pd
import streamlit as st
from config.constants import WORKSHEET_MAIN


def handle_gsheets_error(error):
    """
    統一處理 Google Sheets 錯誤訊息
    """
    error_text = str(error)

    if "429" in error_text:
        st.error("⏳ Google 伺服器繁忙（配額限制），請稍候 30 秒再試。")
    elif "403" in error_text:
        st.error("❌ Google Sheets 權限不足，請檢查金鑰或分享權限。")
    elif "404" in error_text:
        st.error("❌ 找不到指定的工作表，請檢查 worksheet 名稱。")
    else:
        st.error(f"❌ Google Sheets 操作失敗：{error_text}")


def fetch_sheet(conn, worksheet_name, ttl=10):
    """
    通用讀取 Google Sheets 的函式
    """
    if conn is None:
        st.error("❌ Google Sheets 連線尚未初始化。")
        return pd.DataFrame()

    try:
        df = conn.read(worksheet=worksheet_name, ttl=ttl)

        if df is None:
            return pd.DataFrame()

        if not isinstance(df, pd.DataFrame):
            return pd.DataFrame(df)

        return df

    except Exception as e:
        handle_gsheets_error(e)
        return pd.DataFrame()


def fetch_main_assessment_data(conn, ttl=10):
    """
    讀取主評估表（Sheet1）
    """
    return fetch_sheet(conn, WORKSHEET_MAIN, ttl=ttl)


def fetch_main_assessment_data_no_cache(conn):
    """
    讀取主評估表（不使用快取）
    """
    return fetch_sheet(conn, WORKSHEET_MAIN, ttl=0)


def validate_sheet_schema(df, required_columns):
    """
    檢查 DataFrame 是否包含指定欄位
    """
    if df is None or df.empty:
        return False, ["DataFrame 為空"]

    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        return False, missing_columns

    return True, []


def normalize_dataframe_types(df):
    """
    基本型別整理：
    - 所有欄位先保留字串安全性
    - 日期欄位若存在可額外轉換
    """
    if df is None or df.empty:
        return pd.DataFrame()

    normalized_df = df.copy()

    for col in normalized_df.columns:
        try:
            normalized_df[col] = normalized_df[col].fillna("")
        except Exception:
            pass

    return normalized_df


def append_row(conn, worksheet_name, row_df):
    """
    將一列資料 append 到指定 worksheet
    做法：
    1. 先讀舊資料
    2. 再 concat
    3. 最後 update 回去
    """
    if conn is None:
        st.error("❌ Google Sheets 連線尚未初始化。")
        return False

    if row_df is None or row_df.empty:
        st.error("❌ 沒有可寫入的資料。")
        return False

    try:
        existing_df = fetch_sheet(conn, worksheet_name, ttl=0)

        if existing_df is None or existing_df.empty:
            updated_df = row_df.copy()
        else:
            existing_df = normalize_dataframe_types(existing_df)
            row_df = normalize_dataframe_types(row_df)
            updated_df = pd.concat([existing_df, row_df], ignore_index=True)

        conn.update(worksheet=worksheet_name, data=updated_df)
        return True

    except Exception as e:
        handle_gsheets_error(e)
        return False


def write_dataframe(conn, worksheet_name, df):
    """
    直接覆寫整個 worksheet
    """
    if conn is None:
        st.error("❌ Google Sheets 連線尚未初始化。")
        return False

    if df is None:
        st.error("❌ 沒有可寫入的 DataFrame。")
        return False

    try:
        conn.update(worksheet=worksheet_name, data=df)
        return True
    except Exception as e:
        handle_gsheets_error(e)
        return False


def filter_by_patient_id(df, patient_id, patient_id_column="病歷號"):
    """
    依病歷號過濾資料
    """
    if df is None or df.empty:
        return pd.DataFrame()

    if patient_id_column not in df.columns:
        return pd.DataFrame()

    patient_id = str(patient_id).strip()
    working_df = df.copy()
    working_df[patient_id_column] = working_df[patient_id_column].astype(str).str.strip()

    return working_df[working_df[patient_id_column] == patient_id].copy()


def safe_sort_by_datetime(df, datetime_column="日期"):
    """
    依日期欄位排序（新到舊）
    """
    if df is None or df.empty:
        return pd.DataFrame()

    if datetime_column not in df.columns:
        return df

    working_df = df.copy()

    try:
        working_df[datetime_column] = pd.to_datetime(
            working_df[datetime_column], errors="coerce"
        )
        working_df = working_df.sort_values(by=datetime_column, ascending=False)
    except Exception:
        pass

    return working_df