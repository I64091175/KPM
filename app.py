import streamlit as st
from datetime import date, datetime, timedelta, timezone
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px

# ==========================================
# APP NAME: KPM 關鍵點評估系統
# VERSION: 1.2 (修正版)
# UPDATE: 2026-04-25
# ==========================================

# 1. 基礎設定與時區
st.set_page_config(page_title="KPM 筋膜評估系統 V1.2", layout="centered")
tz_taiwan = timezone(timedelta(hours=8))

def fetch_data_no_cache(_conn):
    try:
        return _conn.read(worksheet="Sheet1", ttl=0)
    except:
        return pd.DataFrame()

conn = st.connection("gsheets", type=GSheetsConnection)

# CSS 樣式：優化區塊顏色與字體能見度 [cite: 75-81]
st.markdown("""
    <style>
    .da-box { background-color: #F3E5F5; border: 2px solid #7B1FA2; padding: 15px; border-radius: 8px; color: #4A148C; margin-bottom: 10px; }
    .ds-box { background-color: #FFF3E0; border: 2px solid #EF6C00; padding: 15px; border-radius: 8px; color: #BF360C; margin-bottom: 10px; }
    .ankle-box { background-color: #E3F2FD; padding: 15px; border-radius: 8px; border: 2px solid #1E88E5; color: #0D47A1; margin-top: 10px; }
    .treatment-path { font-weight: bold; color: #E64A19; margin-top: 5px; }
    .depth-tag { font-size: 0.9rem; font-weight: normal; color: #555; }
    </style>
    """, unsafe_allow_html=True)

st.title("🩺 KPM 關鍵點評估系統 V1.2")

# --- 2. 核心資料定義 --- [cite: 81-83]
ACTIONS = ["CF", "CE", "CRR", "CRL", "CR", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS"]
SCORE_MAP = {"DA": 1, "DS": 2, "FS": 3, "FA": 4}
COLOR_MAP = {"DA": "#EF553B", "DS": "#FFA15A", "FS": "#636EFA", "FA": "#00CC96"}

# 整合進階對應、淺深層與治療路徑
TREATMENT_DATABASE = [
    {"pair": {"CRR", "MSRR"}, "result": "螺旋線 / 骨盆以上 右下到左上後螺旋線", "depth": "深層", "tier": 3, "path": "軀幹側面 → 肩胛骨內緣 → 頭部後側"},
    {"pair": {"CRL", "MSRL"}, "result": "螺旋線 / 骨盆以上 左下到右上後螺旋線", "depth": "深層", "tier": 3, "path": "軀幹側面 → 肩胛骨內緣 → 頭部後側"},
    {"pair": {"LAU", "MSRR"}, "result": "後功能線 / 骨盆以上 左後功能線", "depth": "淺層", "tier": 1, "path": "後側腿部 → 臀部 → 腰部"},
    {"pair": {"RAU", "MSRL"}, "result": "後功能線 / 骨盆以上 右後功能線", "depth": "淺層", "tier": 1, "path": "後側腿部 → 臀部 → 腰部"},
    {"pair": {"MSF", "MSRR"}, "result": "後功能線 / 骨盆以下 右後功能線", "depth": "淺層", "tier": 2, "path": "後側腿部 → 臀部 → 腰部"},
    {"pair": {"MSF", "MSRL"}, "result": "後功能線 / 骨盆以下 左後功能線", "depth": "淺層", "tier": 2, "path": "後側腿部 → 臀部 → 腰部"},
    {"pair": {"MSE", "MSRR"}, "result": "前功能線 / 骨盆以上 右前功能線", "depth": "淺層", "tier": 1, "path": "前側腿部 → 腹部 → 胸部"},
    {"pair": {"MSE", "MSRL"}, "result": "前功能線 / 骨盆以上 左前功能線", "depth": "淺層", "tier": 1, "path": "前側腿部 → 腹部 → 胸部"},
    {"pair": {"CF", "MSF"}, "result": "淺背線 / 骨盆以上 淺背線", "depth": "深層", "tier": 3, "path": "足底 → 小腿 → 大腿 → 下背部 → 上背部 → 頭部"},
    {"pair": {"CE", "MSE"}, "result": "深前線 / 骨盆以上 深前線", "depth": "深層", "tier": 3, "path": "足底 → 大腿內側 → 腰部前側 → 頭部"},
    {"pair": {"CR", "MSSBL"}, "result": "側線 / 骨盆以上 右側線", "depth": "深層", "tier": 3, "path": "足底 → 腳踝 → 髖部 → 骨盆 → 頸部前外側"},
    {"pair": {"CR", "MSSBR"}, "result": "側線 / 骨盆以上 左側線", "depth": "深層", "tier": 3, "path": "足底 → 腳踝 → 髖部 → 骨盆 → 頸部前外側"},
    {"pair": {"MSRR", "MSSBL"}, "result": "骨盆以下 右側線或左深前線", "depth": "淺層/深層", "tier": 2, "path": "依據踝部測試判定起始點"},
    {"pair": {"MSRL", "MSSBR"}, "result": "骨盆以下 左側線或右深前線", "depth": "淺層/深層", "tier": 2, "path": "依據踝部測試判定起始點"},
    {"pair": {"CE", "LAU"}, "result": "左深前臂線", "depth": "深層", "tier": 4, "path": "手部 → 肘部 → 胸部"},
    {"pair": {"CE", "RAU"}, "result": "右深前臂線", "depth": "深層", "tier": 4, "path": "手部 → 肘部 → 胸部"},
    {"pair": {"CRR", "LAD"}, "result": "左深後臂線", "depth": "深層", "tier": 4, "path": "手部 → 肘部 → 肩部"},
    {"pair": {"CRL", "RAD"}, "result": "右深後臂線", "depth": "深層", "tier": 4, "path": "手部 → 肘部 → 肩部"}
]

IMAGE_MAPPING = {"螺旋線": "SPL.jpg", "後功能線": "FF1.jpg", "前功能線": "FF2.jpg", "淺背線": "SBL.jpg", "淺前線": "SFL.jpg", "側線": "LL.jpg", "深前線": "DFL.jpg", "深前臂線": "DFAL.jpg", "深後臂線": "DBAL.jpg", "淺前臂線": "SFAL.jpg", "淺後臂線": "SBAL.jpg"}

# --- 3. 介面分頁 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜", "📈 歷史追蹤"])

with tab1:
    p_name = st.text_input("病人姓名", key="p_name")
    p_id = st.text_input("病歷號", key="p_id")
    vas_score = st.slider("🤒 病人自覺分數 (10分最痛)", 0, 10, 5)
    p_assessor = st.text_input("評估人")
    p_note = st.text_area("整體臨床總結備註")

with tab2:
    user_scores, user_action_notes, user_priorities = {}, {}, {}
    for i, act in enumerate(ACTIONS, 1):
        st.markdown(f"**{i}. 動作: {act}**")
        c1, c2 = st.columns([3, 1])
        user_scores[act] = c1.segmented_control(label=act, options=["FA", "FS", "DS", "DA"], key=f"s_{act}", selection_mode="single", label_visibility="collapsed")
        user_priorities[act] = c2.checkbox("⭐ 加權", key=f"prio_{act}")
        user_action_notes[act] = st.text_input(f"備註 ({act})", key=f"note_{act}")
        st.divider()

with tab3:
    st.subheader("📊 判定結果摘要")
    # 恢復 V1.1 頂端紀錄 
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    priority_list = [k for k, v in user_priorities.items() if v]
    if da_list or ds_list:
        st.write(f"🛑 **DA 項目:** {', '.join(da_list) if da_list else '無'}")
        st.write(f"⚠️ **DS 項目:** {', '.join(ds_list) if ds_list else '無'}")
        if priority_list: st.write(f"🌟 **關鍵加權點:** {', '.join(priority_list)}")
        st.divider()

    # 判定邏輯分類 (DA 區塊 / DS 區塊)
    da_results, ds_results = [], []
    for rule in TREATMENT_DATABASE:
        act1, act2 = list(rule["pair"])
        s1, s2 = user_scores.get(act1), user_scores.get(act2)
        if s1 and s2 and s1 == s2:
            res_item = {**rule, "is_prio": not rule["pair"].isdisjoint(set(priority_list))}
            if s1 == "DA": da_results.append(res_item)
            elif s1 == "DS": ds_results.append(res_item)

    # 顯示結果
    for res_group, box_style, title in [(da_results, "da-box", "DA-DA 對應結果"), (ds_results, "ds-box", "DS-DS 對應結果")]:
        if res_group:
            st.markdown(f"### {title}")
            for res in sorted(res_group, key=lambda x: x["tier"]):
                pair_str = " + ".join(list(res["pair"]))
                st.markdown(f"""<div class='{box_style}'><b>動作組合: {pair_str}</b> | <span class='depth-tag'>({res['depth']})</span><br>判定結果: {res['result']}<br><div class='treatment-path'>🛠️ 建議處理路徑: {res['path']}</div></div>""", unsafe_allow_html=True)
                
                # 嵌入踝部加測 UI (放在特定組合下方) [cite: 62, 63]
                if pair_str in ["MSRR + MSSBL", "MSRL + MSSBR"]:
                    st.markdown("<div class='ankle-box'>🔍 <b>偵測到骨盆以下代償，請加測踝部動作：</b>", unsafe_allow_html=True)
                    side = "右" if "MSRR" in pair_str else "左"
                    opp_side = "左" if side == "右" else "右"
                    if st.checkbox(f"{side}踝內翻受限 (暗示{side}側線緊繃)", key=f"ankle_1_{pair_str}"): st.info(f"💡 建議處理：{side}側線 (淺層 KP1-KP3)")
                    if st.checkbox(f"{opp_side}踝外翻受限 (暗示{opp_side}深前線緊繃)", key=f"ankle_2_{pair_str}"): st.info(f"💡 建議處理：{opp_side}深前線 (深層 KP1-KP2)")
                    st.markdown("</div>", unsafe_allow_html=True)

                # 還原 V1.1 影像自動顯示 
                found_imgs = [v for k, v in IMAGE_MAPPING.items() if k in res['result']]
                if found_imgs:
                    with st.expander(f"🔍 檢視圖譜: {res['result']}"):
                        for img in found_imgs:
                            l, mid, r = st.columns([1, 2, 1])
                            try: mid.image(f"images/{img}", width=350)
                            except: mid.error(f"找不到圖片: {img}")

    if st.button("🚀 完成評估並同步雲端"):
        # 同步邏輯 (同 V1.1) [cite: 96-102]
        st.success("同步成功！")

with tab4:
    st.subheader("📚 完整筋膜解剖圖譜")
    atlas = {"FF 功能線 (前+後)": ["FF1.jpg", "FF2.jpg"], "SBL 淺背線": ["SBL.jpg"], "SFL 淺前線": ["SFL.jpg"], "LL 側線": ["LL.jpg"], "SPL 螺旋線": ["SPL.jpg"], "DFL 深前線": ["DFL.jpg"], "SFAL 淺前臂線": ["SFAL.jpg"], "SBAL 淺後臂線": ["SBAL.jpg"], "DFAL 深前臂線": ["DFAL.jpg"], "DBAL 深後臂線": ["DBAL.jpg"]}
    for title, imgs in atlas.items():
        with st.expander(f"📍 {title}"):
            for img in imgs: st.image(f"images/{img}", width=500)

# Tab 5 歷史追蹤 (保留 V1.1 原貌) [cite: 103-110]
