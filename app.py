# ==========================================
# APP NAME: KPM 關鍵點評估系統
# VERSION: 1.1 (臨床決策加權版)
# BASE: V1.01 穩定地基
# UPDATE: 2026-04-08
# FEATURES: 
#   - CR 動作調整至第 5 位
#   - 新增 VAS 病人自覺分數滑桿 (0-10)
#   - 新增 ⭐ 關鍵點加權功能 (一鍵置頂重點)
#   - 自動修正時區 (UTC+8) 與 歷史圖表 (補) 字樣顯示
#   - 流量 429 報錯隱藏與中文友善提示
# ==========================================
import streamlit as st
from datetime import date, datetime, timedelta, timezone
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px
import google.generativeai as genai

# 1. 基礎設定與初始化
st.set_page_config(page_title="KPM 筋膜評估系統 V1.1", layout="centered")
tz_taiwan = timezone(timedelta(hours=8))

# API 連接
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.sidebar.error("API 金鑰設定錯誤")

def fetch_data_no_cache(_conn):
    try:
        return _conn.read(worksheet="Sheet1", ttl=0)
    except Exception as e:
        if "429" in str(e):
            st.error("⚠️ 系統連線繁忙，請等候約 60 秒。")
        return pd.DataFrame()

conn = st.connection("gsheets", type=GSheetsConnection)

# CSS 樣式
st.markdown("""
    <style>
    .action-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 5px; color: #1E88E5; }
    .superficial-header { color: #2E7D32; font-weight: bold; border-left: 5px solid #2E7D32; padding-left: 10px; margin-top: 20px; }
    .deep-box { background-color: #FFF3E0; border-left: 5px solid #EF6C00; padding: 15px; border-radius: 8px; color: #BF360C; margin-bottom: 10px; }
    .priority-box { background-color: #F3E5F5; border: 2px solid #7B1FA2; padding: 15px; border-radius: 8px; color: #4A148C; margin-bottom: 15px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🩺 KPM 關鍵點評估系統 V1.1")

# 資料定義
ACTIONS = ["CF", "CE", "CRR", "CRL", "CR", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS"]
SCORE_MAP = {"DA": 1, "DS": 2, "FS": 3, "FA": 4}
COLOR_MAP = {"DA": "#EF553B", "DS": "#FFA15A", "FS": "#636EFA", "FA": "#00CC96"}

TREATMENT_DATABASE = [
    {"pair": {"CRR", "MSRR"}, "result": "螺旋線 / 骨盆以上 右下到左上後螺旋線"},
    {"pair": {"CRL", "MSRL"}, "result": "螺旋線 / 骨盆以上 左下到右上後螺旋線"},
    {"pair": {"LAU", "MSRR"}, "result": "後功能線 / 骨盆以上 左後功能線"},
    {"pair": {"RAU", "MSRL"}, "result": "後功能線 / 骨盆以上 右後功能線"},
    {"pair": {"MSF", "MSRR"}, "result": "後功能線 / 骨盆以下 右後功能線"},
    {"pair": {"MSF", "MSRL"}, "result": "後功能線 / 骨盆以下 左後功能線"},
    {"pair": {"MSE", "MSRR"}, "result": "前功能線 / 骨盆以上 右前功能線"},
    {"pair": {"MSE", "MSRL"}, "result": "前功能線 / 骨盆以上 左前功能線"},
    {"pair": {"CF", "MSF"}, "result": "淺背線 / 骨盆以上 淺背線"},
    {"pair": {"CE", "MSE"}, "result": "深前線 / 骨盆以上 深前線"},
    {"pair": {"CR", "MSSBL"}, "result": "側線 / 骨盆以上 右側線"},
    {"pair": {"CR", "MSSBR"}, "result": "側線 / 骨盆以上 左側線"},
    {"pair": {"MSRR", "MSSBL"}, "result": "骨盆以下 右側線或左深前線"},
    {"pair": {"MSRL", "MSSBR"}, "result": "骨盆以下 左側線或右深前線"},
    {"pair": {"CE", "LAU"}, "result": "深前臂線 / 左深前臂線"},
    {"pair": {"CE", "RAU"}, "result": "深前臂線 / 右深前臂線"},
    {"pair": {"CRR", "LAD"}, "result": "深後臂線 / 左深後臂線"},
    {"pair": {"CRL", "RAD"}, "result": "深後臂線 / 右深後臂線"},
]

DEEP_PAIRS = [{"CE", "MSE"}, {"MSRR", "MSSBL"}, {"MSRL", "MSSBR"}, {"CE", "LAU"}, {"CE", "RAU"}, {"CRR", "LAD"}, {"CRL", "RAD"}]

# 分頁結構
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜", "📈 歷史追蹤"])

with tab1:
    p_name = st.text_input("病人姓名")
    p_id = st.text_input("病歷號")
    p_date = st.date_input("評估日期", value=datetime.now(tz_taiwan).date())
    vas_score = st.slider("🤒 病人自覺整體分數 (10分最痛 / 0分不痛)", 0, 10, 5)
    p_assessor = st.text_input("評估人")
    p_note = st.text_area("整體臨床總結備註")

with tab2:
    user_scores, user_action_notes, user_priorities = {}, {}, {}
    for act in ACTIONS:
        st.markdown(f"<div class='action-title'>動作: {act}</div>", unsafe_allow_html=True)
        c1, c2 = st.columns([3, 1])
        user_scores[act] = c1.segmented_control(label=act, options=["FA", "FS", "DS", "DA"], key=f"s_{act}", selection_mode="single", label_visibility="collapsed")
        user_priorities[act] = c2.checkbox("⭐ 加權", key=f"prio_{act}")
        user_action_notes[act] = st.text_input(f"備註 ({act})", key=f"note_{act}")
        st.divider()

with tab3:
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    priority_list = [k for k, v in user_priorities.items() if v]
    matched_results = []
    for rule in TREATMENT_DATABASE:
        if rule["pair"].issubset(set(da_list if da_list else [k for k, v in user_scores.items() if v == "DS"])):
            matched_results.append({"rule": rule, "is_prio": not rule["pair"].isdisjoint(set(priority_list))})
    
    for item in sorted(matched_results, key=lambda x: x["is_prio"], reverse=True):
        m, is_prio = item["rule"], item["is_prio"]
        if is_prio: st.markdown(f"<div class='priority-box'>🔥 重點處理<br>結果: {m['result']}</div>", unsafe_allow_html=True)
        elif m["pair"] in DEEP_PAIRS: st.markdown(f"<div class='deep-box'><strong>💎 深層</strong><br>結果: {m['result']}</div>", unsafe_allow_html=True)
        else: st.success(f"🌿 {m['result']}")

    if st.button("🚀 同步雲端"):
        record = {"日期": datetime.now(tz_taiwan).strftime("%Y-%m-%d %H:%M"), "病人姓名": p_name, "病歷號": f"'{p_id}", "病人自覺分數": vas_score, "判定結果": " / ".join([res['rule']['result'] for res in matched_results])}
        record.update(user_scores)
        conn.update(worksheet="Sheet1", data=pd.concat([fetch_data_no_cache(conn), pd.DataFrame([record])], ignore_index=True))
        st.success("同步成功！")
