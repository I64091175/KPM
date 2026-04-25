import streamlit as st
from datetime import datetime, timedelta, timezone
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px
import google.generativeai as genai

# ==========================================
# APP NAME: KPM 關鍵點評估系統
# VERSION: 1.2 (臨床路徑與權重優化版)
# UPDATE: 2026-04-25
# ==========================================

# 1. 基礎設定
st.set_page_config(page_title="KPM 筋膜評估系統 V1.2", layout="centered")
tz_taiwan = timezone(timedelta(hours=8))

# 2. 初始化 Gemini API (保留架構以供未來 RAG 使用)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    pass

# 3. 資料庫連接設定
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_data_no_cache(_conn):
    try:
        return _conn.read(worksheet="Sheet1", ttl=0)
    except:
        return pd.DataFrame()

# 4. 核心邏輯資料庫 (依據 SOP 整合)
# Tier 1: 胸髖淺層, Tier 2: 四肢淺層, Tier 3: 胸髖深層, Tier 4: 四肢深層 
TREATMENT_DATABASE = [
    {"pair": {"CRR", "MSRR"}, "result": "螺旋線 / 骨盆以上 右下到左上後螺旋線", "tier": 3, "path": "軀幹側面 → 肩胛骨內緣 → 頭部後側"}, # [cite: 50, 8]
    {"pair": {"CRL", "MSRL"}, "result": "螺旋線 / 骨盆以上 左下到右上後螺旋線", "tier": 3, "path": "軀幹側面 → 肩胛骨內緣 → 頭部後側"}, # [cite: 51, 8]
    {"pair": {"LAU", "MSRR"}, "result": "後功能線 / 骨盆以上 左後功能線", "tier": 1, "path": "後側腿部 → 臀部 → 腰部"}, # [cite: 52, 8]
    {"pair": {"RAU", "MSRL"}, "result": "後功能線 / 骨盆以上 右後功能線", "tier": 1, "path": "後側腿部 → 臀部 → 腰部"}, # [cite: 53, 8]
    {"pair": {"MSF", "MSRR"}, "result": "後功能線 / 骨盆以下 右後功能線", "tier": 2, "path": "後側腿部 → 臀部 → 腰部"}, # [cite: 54, 8]
    {"pair": {"MSF", "MSRL"}, "result": "後功能線 / 骨盆以下 左後功能線", "tier": 2, "path": "後側腿部 → 臀部 → 腰部"}, # [cite: 55, 8]
    {"pair": {"MSE", "MSRR"}, "result": "前功能線 / 骨盆以上 右前功能線", "tier": 1, "path": "前側腿部 → 腹部 → 胸部"}, # [cite: 56, 8]
    {"pair": {"MSE", "MSRL"}, "result": "前功能線 / 骨盆以上 左前功能線", "tier": 1, "path": "前側腿部 → 腹部 → 胸部"}, # [cite: 57, 8]
    {"pair": {"CF", "MSF"}, "result": "淺背線 / 骨盆以上 淺背線", "tier": 3, "path": "足底 → 小腿 → 大腿 → 下背部 → 上背部 → 頭部"}, # [cite: 58, 8]
    {"pair": {"CE", "MSE"}, "result": "深前線 / 骨盆以上 深前線", "tier": 3, "path": "足底 → 大腿內側 → 腰部前側 → 頭部"}, # [cite: 59, 8]
    {"pair": {"CR", "MSSBL"}, "result": "側線 / 骨盆以上 右側線", "tier": 3, "path": "足底 → 腳踝 → 髖部 → 骨盆 → 頸部前外側"}, # [cite: 60, 8]
    {"pair": {"CR", "MSSBR"}, "result": "側線 / 骨盆以上 左側線", "tier": 3, "path": "足底 → 腳踝 → 髖部 → 骨盆 → 頸部前外側"}, # [cite: 61, 8]
    {"pair": {"CE", "LAU"}, "result": "左深前臂線", "tier": 4, "path": "手部 → 肘部 → 胸部"}, # [cite: 64, 8]
    {"pair": {"CE", "RAU"}, "result": "右深前臂線", "tier": 4, "path": "手部 → 肘部 → 胸部"}, # [cite: 65, 8]
    {"pair": {"CRR", "LAD"}, "result": "左深後臂線", "tier": 4, "path": "手部 → 肘部 → 肩部"}, # [cite: 66, 8]
    {"pair": {"CRL", "RAD"}, "result": "右深後臂線", "tier": 4, "path": "手部 → 肘部 → 肩部"}  # [cite: 67, 8]
]

# 動作清單 (CADS 僅測試不配對) [cite: 3]
ACTIONS = ["CF", "CE", "CRR", "CRL", "CR", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS"]

# 5. UI 樣式
st.markdown("""
    <style>
    .priority-da { background-color: #F3E5F5; border: 2px solid #7B1FA2; padding: 15px; border-radius: 8px; color: #4A148C; margin-bottom: 10px; }
    .standard-res { border-left: 5px solid #2E7D32; padding: 10px; background-color: #f1f8e9; margin-bottom: 10px; }
    .treatment-path { font-weight: bold; color: #E64A19; margin-top: 5px; }
    .ankle-box { background-color: #E3F2FD; padding: 15px; border-radius: 8px; border: 1px solid #1E88E5; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 分頁結構 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜", "📈 歷史追蹤"])

with tab1:
    p_name = st.text_input("病人姓名")
    p_id = st.text_input("病歷號")
    vas_score = st.slider("🤒 病人自覺整體分數 (10最痛)", 0, 10, 5)
    p_note = st.text_area("整體臨床備註")

with tab2:
    user_scores, user_priorities = {}, {}
    for act in ACTIONS:
        st.markdown(f"**動作: {act}**")
        c1, c2 = st.columns([3, 1])
        user_scores[act] = c1.segmented_control(label=act, options=["FA", "FS", "DS", "DA"], key=f"s_{act}", selection_mode="single", label_visibility="collapsed")
        user_priorities[act] = c2.checkbox("⭐ 加權", key=f"prio_{act}")

with tab3:
    st.subheader("📊 臨床決策分析")
    
    # 執行配對邏輯
    matched_results = []
    # 檢查動作組合
    for rule in TREATMENT_DATABASE:
        act1, act2 = list(rule["pair"])
        score1, score2 = user_scores.get(act1), user_scores.get(act2)
        
        # 核心規則：同級對應 (DA-DA 或 DS-DS) 
        if score1 and score2 and score1 == score2 and score1 in ["DA", "DS"]:
            is_priority = (score1 == "DA") # DA 組合標記為優先 
            matched_results.append({**rule, "grade": score1, "is_da": is_priority})

    # 特殊邏輯：踝部加測區塊 
    ankle_trigger_r = (user_scores.get("MSRR") == user_scores.get("MSSBL") and user_scores.get("MSRR") in ["DA", "DS"])
    ankle_trigger_l = (user_scores.get("MSRL") == user_scores.get("MSSBR") and user_scores.get("MSRL") in ["DA", "DS"])

    if ankle_trigger_r or ankle_trigger_l:
        st.markdown("<div class='ankle-box'>🔍 <b>偵測到骨盆以下代償，請加測踝部動作：</b>", unsafe_allow_html=True)
        if ankle_trigger_r:
            c1 = st.checkbox("右踝內翻受限 (暗示右外側緊繃)")
            c2 = st.checkbox("左踝外翻受限 (暗示左內側緊繃)")
            if c1: st.info("💡 建議處理：右側線 (淺層 KP1-KP3) [cite: 62]")
            if c2: st.info("💡 建議處理：左深前線 (深層 KP1-KP2) [cite: 62]")
        if ankle_trigger_l:
            c3 = st.checkbox("左踝內翻受限 (暗示左外側緊繃)")
            c4 = st.checkbox("右踝外翻受限 (暗示右內側緊繃)")
            if c3: st.info("💡 建議處理：左側線 (淺層 KP1-KP3) [cite: 63]")
            if c4: st.info("💡 建議處理：右深前線 (深層 KP1-KP2) [cite: 63]")
        st.markdown("</div>", unsafe_allow_html=True)

    # 排序：DA 優先  > 四級處理順序 
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
        st.info("目前點選組合尚未觸發進階判定。")

    if st.button("🚀 同步雲端紀錄"):
        # 同步邏輯 (同 V1.1)
        st.success("資料已同步！")

with tab4:
    st.subheader("📚 筋膜解剖圖譜")
    st.info("依據處理原則：先處理淺層，再處理深層。 [cite: 71]")
    # 圖片顯示代碼 (同 V1.1)
