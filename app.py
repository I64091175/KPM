# ==========================================
# APP NAME: KPM 關鍵點評估系統
# VERSION: 1.1 (臨床決策加權版 + AI 模組)
# UPDATE: 2026-04-20
# FEATURES: 
#   - CR 調整至第 5 位
#   - 新增 VAS 分數滑桿 & 自動擴充 Excel 欄位
#   - 新增 ⭐ 加權與重點置頂顯示
#   - 整合 Gemini API (1.5-flash)
# ==========================================

import streamlit as st
from datetime import date, datetime, timedelta, timezone
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px
import google.generativeai as genai

# 1. 基礎設定與時區
st.set_page_config(page_title="KPM 筋膜評估系統 V1.1", layout="centered")
tz_taiwan = timezone(timedelta(hours=8))

# 2. 初始化 Gemini API
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.sidebar.error("API 金鑰未設定或設定錯誤，請檢查 secrets.toml")

def fetch_data_no_cache(_conn):
    try:
        return _conn.read(worksheet="Sheet1", ttl=0)
    except Exception as e:
        if "429" in str(e):
            st.error("⚠️ 系統連線繁忙，請等候約 60 秒後重新整理網頁。")
        else:
            st.error(f"讀取資料庫失敗: {e}")
        return pd.DataFrame()

conn = st.connection("gsheets", type=GSheetsConnection)

# CSS 樣式
st.markdown("""
    <style>
    .stHeader { font-size: 1.2rem !important; color: #2c3e50; }
    .action-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 5px; color: #1E88E5; }
    .superficial-header { color: #2E7D32; font-weight: bold; border-left: 5px solid #2E7D32; padding-left: 10px; margin-top: 20px; }
    .deep-box { background-color: #FFF3E0; border-left: 5px solid #EF6C00; padding: 15px; border-radius: 8px; color: #BF360C; margin-bottom: 10px; }
    .priority-box { background-color: #F3E5F5; border: 2px solid #7B1FA2; padding: 15px; border-radius: 8px; color: #4A148C; margin-bottom: 15px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🩺 KPM 關鍵點評估系統 V1.1")

# --- 側邊欄 AI 測試 ---
if st.sidebar.button("測試 AI 連線"):
    try:
        response = model.generate_content("請回覆：連線成功")
        st.sidebar.success(response.text)
    except Exception as e:
        st.sidebar.error(f"連線失敗: {e}")

# --- 核心資料定義 ---
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

IMAGE_MAPPING = {"螺旋線": "SPL.jpg", "後功能線": "FF1.jpg", "前功能線": "FF2.jpg", "淺背線": "SBL.jpg", "淺前線": "SFL.jpg", "側線": "LL.jpg", "深前線": "DFL.jpg", "深前臂線": "DFAL.jpg", "深後臂線": "DBAL.jpg", "淺前臂線": "SFAL.jpg", "淺後臂線": "SBAL.jpg"}
DEEP_PAIRS = [{"CE", "MSE"}, {"MSRR", "MSSBL"}, {"MSRL", "MSSBR"}, {"CE", "LAU"}, {"CE", "RAU"}, {"CRR", "LAD"}, {"CRL", "RAD"}]

# --- 分頁 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜", "📈 歷史追蹤"])

with tab1:
    st.subheader("👤 病人基本資料")
    p_name = st.text_input("病人姓名", key="p_name")
    p_id = st.text_input("病歷號/身分證號", key="p_id", placeholder="例如: 00123")
    today_taiwan = datetime.now(tz_taiwan).date()
    p_date = st.date_input("評估日期", value=today_taiwan)
    vas_score = st.slider("🤒 病人自覺整體分數 (10分最痛 / 0分不痛)", 0, 10, 5)
    p_assessor = st.text_input("評估人", key="p_assessor")
    p_note = st.text_area("整體臨床總結備註", height=100)

with tab2:
    user_scores, user_action_notes, user_priorities = {}, {}, {}
    for i, act in enumerate(ACTIONS, 1):
        st.markdown(f"<div class='action-title'>{i}. 動作: {act}</div>", unsafe_allow_html=True)
        c1, c2 = st.columns([3, 1])
        user_scores[act] = c1.segmented_control(label=act, options=["FA", "FS", "DS", "DA"], key=f"s_{act}", selection_mode="single", label_visibility="collapsed")
        user_priorities[act] = c2.checkbox("⭐ 加權", key=f"prio_{act}")
        user_action_notes[act] = st.text_input(f"備註 ({act})", key=f"note_{act}")
        st.divider()

with tab3:
    st.subheader("📊 判定結果摘要")
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    priority_list = [k for k, v in user_priorities.items() if v]
    
    if da_list or ds_list:
        st.write(f"🛑 DA: {', '.join(da_list)}")
        st.write(f"⚠️ DS: {', '.join(ds_list)}")
        st.divider()

    matched_results = []
    source = da_list if da_list else ds_list
    for rule in TREATMENT_DATABASE:
        if rule["pair"].issubset(set(source)):
            matched_results.append({"rule": rule, "is_prio": not rule["pair"].isdisjoint(set(priority_list))})
    
    for item in sorted(matched_results, key=lambda x: x["is_prio"], reverse=True):
        m, is_prio = item["rule"], item["is_prio"]
        if is_prio: st.markdown(f"<div class='priority-box'>🔥 重點處理<br>動作: {' + '.join(list(m['pair']))}<br>結果: {m['result']}</div>", unsafe_allow_html=True)
        elif m["pair"] in DEEP_PAIRS: st.markdown(f"<div class='deep-box'><strong>💎 深層</strong><br>結果: {m['result']}</div>", unsafe_allow_html=True)
        else: st.success(f"🌿 {m['result']}")

    if st.button("🚀 完成評估並同步雲端"):
        try:
            act_notes = [f"{a}:{user_action_notes[a].strip()}" for a in ACTIONS if user_action_notes[a].strip()]
            final_note = f"{p_note} | 詳細: {'/'.join(act_notes + [f'{a}(⭐)' for a in priority_list])}"
            now_tw = datetime.now(tz_taiwan)
            final_dt = now_tw.strftime("%Y-%m-%d %H:%M") if p_date >= now_tw.date() else f"{p_date} (補)"
            
            record = {"日期": final_dt, "病人姓名": p_name, "病歷號": f"'{p_id}", "病人自覺分數": vas_score, "加權關鍵點": ", ".join(priority_list), "判定結果": " / ".join([res['rule']['result'] for res in matched_results]), "備註": final_note}
            record.update(user_scores)
            conn.update(worksheet="Sheet1", data=pd.concat([fetch_data_no_cache(conn), pd.DataFrame([record])], ignore_index=True))
            st.balloons(); st.success("✅ 同步成功！")
        except Exception as e:
            st.error("同步失敗，請稍候再試")

with tab5:
    st.subheader("📈 歷史趨勢")
    search_id = st.text_input("病歷號查詢")
    if search_id:
        df = fetch_data_no_cache(conn)
        p_history = df[df['病歷號'].astype(str).str.contains(search_id)].sort_values("日期")
        st.plotly_chart(px.bar(p_history, x="日期", y="病人自覺分數", text="病人自覺分數").update_layout(xaxis_type='category'))
        st.dataframe(p_history)
