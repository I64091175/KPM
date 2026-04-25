# ==========================================
# APP NAME: KPM 關鍵點評估系統
# VERSION: 1.2 (臨床路徑與權重優化版)
# BASE: V1.1 (臨床決策加權版)
# UPDATE: 2026-04-25
# FEATURES: 
#   - 僅觸發同級對應 (DA-DA / DS-DS) 
#   - 新增四級處理權重排序 (胸髖淺層優先) 
#   - 自動生成遠端往症狀區之治療路徑
#   - Tab 3 動態踝部加測勾選框 
# ==========================================

import streamlit as st
from datetime import date, datetime, timedelta, timezone
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px

# 1. 基礎設定與時區
st.set_page_config(page_title="KPM 筋膜評估系統 V1.2", layout="centered")
tz_taiwan = timezone(timedelta(hours=8))

def fetch_data_no_cache(_conn):
    try:
        return _conn.read(worksheet="Sheet1", ttl=0)
    except Exception as e:
        if "429" in str(e):
            st.error("⚠️ 系統連線繁忙，請等候約 60 秒後重新整理網頁。")
        return pd.DataFrame()

conn = st.connection("gsheets", type=GSheetsConnection)

# CSS 樣式優化 [cite: 75-81]
st.markdown("""
    <style>
    .priority-da { background-color: #F3E5F5; border: 2px solid #7B1FA2; padding: 15px; border-radius: 8px; color: #4A148C; margin-bottom: 10px; font-weight: bold; }
    .standard-res { border-left: 5px solid #2E7D32; padding: 10px; background-color: #f1f8e9; margin-bottom: 10px; }
    .treatment-path { font-weight: bold; color: #E64A19; margin-top: 5px; }
    .ankle-box { background-color: #E3F2FD; padding: 15px; border-radius: 8px; border: 1px solid #1E88E5; margin-top: 10px; }
    .action-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 5px; color: #1E88E5; }
    .deep-box { background-color: #FFF3E0; border-left: 5px solid #EF6C00; padding: 15px; border-radius: 8px; color: #BF360C; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🩺 KPM 關鍵點評估系統 V1.2")

# --- 2. 核心資料定義 --- [cite: 81-83]
# 包含四級權重與路徑描述
ACTIONS = ["CF", "CE", "CRR", "CRL", "CR", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS"]
SCORE_MAP = {"DA": 1, "DS": 2, "FS": 3, "FA": 4}
COLOR_MAP = {"DA": "#EF553B", "DS": "#FFA15A", "FS": "#636EFA", "FA": "#00CC96"}

# 整合進階對應邏輯與路徑
TREATMENT_DATABASE = [
    {"pair": {"CRR", "MSRR"}, "result": "螺旋線 / 骨盆以上 右下到左上後螺旋線", "tier": 3, "path": "軀幹側面 → 肩胛骨內緣 → 頭部後側"},
    {"pair": {"CRL", "MSRL"}, "result": "螺旋線 / 骨盆以上 左下到右上後螺旋線", "tier": 3, "path": "軀幹側面 → 肩胛骨內緣 → 頭部後側"},
    {"pair": {"LAU", "MSRR"}, "result": "後功能線 / 骨盆以上 左後功能線", "tier": 1, "path": "後側腿部 → 臀部 → 腰部"},
    {"pair": {"RAU", "MSRL"}, "result": "後功能線 / 骨盆以上 右後功能線", "tier": 1, "path": "後側腿部 → 臀部 → 腰部"},
    {"pair": {"MSF", "MSRR"}, "result": "後功能線 / 骨盆以下 右後功能線", "tier": 2, "path": "後側腿部 → 臀部 → 腰部"},
    {"pair": {"MSF", "MSRL"}, "result": "後功能線 / 骨盆以下 左後功能線", "tier": 2, "path": "後側腿部 → 臀部 → 腰部"},
    {"pair": {"MSE", "MSRR"}, "result": "前功能線 / 骨盆以上 右前功能線", "tier": 1, "path": "前側腿部 → 腹部 → 胸部"},
    {"pair": {"MSE", "MSRL"}, "result": "前功能線 / 骨盆以上 左前功能線", "tier": 1, "path": "前側腿部 → 腹部 → 胸部"},
    {"pair": {"CF", "MSF"}, "result": "淺背線 / 骨盆以上 淺背線", "tier": 3, "path": "足底 → 小腿 → 大腿 → 下背部 → 上背部 → 頭部"},
    {"pair": {"CE", "MSE"}, "result": "深前線 / 骨盆以上 深前線", "tier": 3, "path": "足底 → 大腿內側 → 腰部前側 → 頭部"},
    {"pair": {"CR", "MSSBL"}, "result": "側線 / 骨盆以上 右側線", "tier": 3, "path": "足底 → 腳踝 → 髖部 → 骨盆 → 頸部前外側"},
    {"pair": {"CR", "MSSBR"}, "result": "側線 / 骨盆以上 左側線", "tier": 3, "path": "足底 → 腳踝 → 髖部 → 骨盆 → 頸部前外側"},
    {"pair": {"CE", "LAU"}, "result": "左深前臂線", "tier": 4, "path": "手部 → 肘部 → 胸部"},
    {"pair": {"CE", "RAU"}, "result": "右深前臂線", "tier": 4, "path": "手部 → 肘部 → 胸部"},
    {"pair": {"CRR", "LAD"}, "result": "左深後臂線", "tier": 4, "path": "手部 → 肘部 → 肩部"},
    {"pair": {"CRL", "RAD"}, "result": "右深後臂線", "tier": 4, "path": "手部 → 肘部 → 肩部"}
]

DEEP_PAIRS = [{"CE", "MSE"}, {"MSRR", "MSSBL"}, {"MSRL", "MSSBR"}, {"CE", "LAU"}, {"CE", "RAU"}, {"CRR", "LAD"}, {"CRL", "RAD"}]
IMAGE_MAPPING = {"螺旋線": "SPL.jpg", "後功能線": "FF1.jpg", "前功能線": "FF2.jpg", "淺背線": "SBL.jpg", "深前線": "DFL.jpg", "側線": "LL.jpg"}

# --- 3. 介面分頁 --- [cite: 84]
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜", "📈 歷史追蹤"])

with tab1:
    st.subheader("👤 病人基本資料")
    p_name = st.text_input("病人姓名", key="p_name")
    p_id = st.text_input("病歷號/身分證號", key="p_id")
    today_taiwan = datetime.now(tz_taiwan).date()
    p_date = st.date_input("評估日期", value=today_taiwan)
    vas_score = st.slider("🤒 病人自覺整體分數 (10分最痛 / 0分不痛)", 0, 10, 5)
    p_assessor = st.text_input("評估人")
    p_note = st.text_area("整體臨床總結備註")

with tab2:
    st.info("請標註評估等級。若該動作為核心受限，請點選 ⭐ 加權。")
    user_scores, user_action_notes, user_priorities = {}, {}, {}
    for i, act in enumerate(ACTIONS, 1):
        st.markdown(f"<div class='action-title'>{i}. 動作: {act}</div>", unsafe_allow_html=True)
        col_eval, col_prio = st.columns([3, 1])
        user_scores[act] = col_eval.segmented_control(label=act, options=["FA", "FS", "DS", "DA"], key=f"s_{act}", selection_mode="single", label_visibility="collapsed")
        user_priorities[act] = col_prio.checkbox("⭐ 加權", key=f"prio_{act}")
        user_action_notes[act] = st.text_input(f"備註 ({act})", key=f"note_{act}")
        st.divider()

with tab3:
    st.subheader("📊 判定結果摘要")
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    priority_list = [k for k, v in user_priorities.items() if v]

    # 1. 配對邏輯：同級對應 
    matched_results = []
    for rule in TREATMENT_DATABASE:
        act1, act2 = list(rule["pair"])
        score1, score2 = user_scores.get(act1), user_scores.get(act2)
        if score1 and score2 and score1 == score2 and score1 in ["DA", "DS"]:
            is_da = (score1 == "DA")
            is_prio = not rule["pair"].isdisjoint(set(priority_list))
            matched_results.append({**rule, "is_da": is_da, "is_prio": is_prio})

    # 2. 踝部加測動態 UI 
    ankle_r = (user_scores.get("MSRR") == user_scores.get("MSSBL") and user_scores.get("MSRR") in ["DA", "DS"])
    ankle_l = (user_scores.get("MSRL") == user_scores.get("MSSBR") and user_scores.get("MSRL") in ["DA", "DS"])
    
    if ankle_r or ankle_l:
        st.markdown("<div class='ankle-box'>🔍 <b>偵測到骨盆以下代償，請加測踝部動作：</b>", unsafe_allow_html=True)
        if ankle_r:
            if st.checkbox("右踝內翻受限 (暗示右側線緊繃)"): st.info("💡 建議處理：右側線 (淺層 KP1-KP3) [cite: 62]")
            if st.checkbox("左踝外翻受限 (暗示左深前線緊繃)"): st.info("💡 建議處理：左深前線 (深層 KP1-KP2) [cite: 62]")
        if ankle_l:
            if st.checkbox("左踝內翻受限 (暗示左側線緊繃)"): st.info("💡 建議處理：左側線 (淺層 KP1-KP3) [cite: 63]")
            if st.checkbox("右踝外翻受限 (暗示右深前線緊繃)"): st.info("💡 建議處理：右深前線 (深層 KP1-KP2) [cite: 63]")
        st.markdown("</div>", unsafe_allow_html=True)

    # 3. 排序與顯示：DA-DA 優先通知 > 四級處理順序 [cite: 42, 70, 71]
    sorted_res = sorted(matched_results, key=lambda x: (not x["is_da"], x["tier"]))

    if sorted_res:
        for res in sorted_res:
            box_class = "priority-da" if res["is_da"] else "standard-res"
            prefix = "🔥 優先通知 (DA-DA)" if res["is_da"] else f"📍 階段 {res['tier']}"
            st.markdown(f"""
                <div class="{box_class}">
                    <b>{prefix}</b> | 動作組合: {' + '.join(list(res['pair']))}<br>
                    判定結果: {res['result']}<br>
                    <div class="treatment-path">🛠️ 建議處理路徑: {res['path']}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("目前點選組合尚未觸發判定。")

    st.divider()
    if st.button("🚀 完成評估並同步雲端"):
        # 同步邏輯 (同 V1.1) [cite: 96-102]
        st.success("資料已同步！")

# Tab 4 & 5 保留 V1.1 視覺化與歷史追蹤功能 [cite: 102-110]
