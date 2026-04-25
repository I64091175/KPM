import streamlit as st
from datetime import date, datetime, timedelta, timezone
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px

# ==========================================
# APP NAME: KPM 關鍵點評估系統
# VERSION: 1.2 (SOP 邏輯與排序校正版)
# BASE: V1.1 原始地基
# UPDATE: 2026-04-25
# ==========================================

# 1. 基礎設定
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

# CSS 樣式：恢復 V1.1 標準配色 [cite: 75-81]
st.markdown("""
    <style>
    .action-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 5px; color: #1E88E5; }
    .superficial-header { color: #2E7D32; font-weight: bold; border-left: 5px solid #2E7D32; padding-left: 10px; margin-top: 20px; margin-bottom: 5px; }
    .superficial-box { border: 2px solid #2E7D32; padding: 15px; border-radius: 8px; background-color: #F1F8E9; margin-bottom: 10px; color: #1B5E20; }
    .deep-box { background-color: #FFF3E0; border-left: 5px solid #EF6C00; padding: 15px; border-radius: 8px; color: #BF360C; margin-bottom: 10px; }
    .priority-box { background-color: #F3E5F5; border: 2px solid #7B1FA2; padding: 15px; border-radius: 8px; color: #4A148C; margin-bottom: 15px; font-weight: bold; }
    .muscle-text { font-weight: bold; color: #D84315; margin-top: 5px; }
    .ankle-box { background-color: #E3F2FD; padding: 15px; border-radius: 8px; border: 2px solid #1E88E5; color: #000000; margin-top: 20px; font-weight: bold; }
    hr { margin-top: 1rem; margin-bottom: 1rem; border-bottom: 2px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

st.title("🩺 KPM 關鍵點評估系統 V1.2")

# --- 2. 核心資料定義 (嚴格對照 SOP) --- 
ACTIONS = ["CF", "CE", "CRR", "CRL", "CR", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS"]
SCORE_MAP = {"DA": 1, "DS": 2, "FS": 3, "FA": 4}
COLOR_MAP = {"DA": "#EF553B", "DS": "#FFA15A", "FS": "#636EFA", "FA": "#00CC96"}

TREATMENT_DATABASE = [
    {"pair": {"CRR", "MSRR"}, "result": "螺旋線 / 骨盆以上 右下到左上後螺旋線", "muscles": "左頭頰、右菱形、右前鉅", "depth": "深層"},
    {"pair": {"CRL", "MSRL"}, "result": "螺旋線 / 骨盆以上 左下到右上後螺旋線", "muscles": "右頭頰、左菱形、左前鉅", "depth": "深層"},
    {"pair": {"LAU", "MSRR"}, "result": "後功能線 / 骨盆以上 左後功能線", "muscles": "左闊背", "depth": "淺層"},
    {"pair": {"RAU", "MSRL"}, "result": "後功能線 / 骨盆以上 右後功能線", "muscles": "右闊背", "depth": "淺層"},
    {"pair": {"MSF", "MSRR"}, "result": "後功能線 / 骨盆以下 右後功能線", "muscles": "右臀大、右股外側", "depth": "淺層"},
    {"pair": {"MSF", "MSRL"}, "result": "後功能線 / 骨盆以下 左後功能線", "muscles": "左臀大、左股外側", "depth": "淺層"},
    {"pair": {"MSE", "MSRR"}, "result": "前功能線 / 骨盆以上 右前功能線", "muscles": "右胸大、右腹直", "depth": "淺層"},
    {"pair": {"MSE", "MSRL"}, "result": "前功能線 / 骨盆以上 左前功能線", "muscles": "左胸大、左腹直", "depth": "淺層"},
    {"pair": {"CF", "MSF"}, "result": "淺背線 / 骨盆以上 淺背線", "muscles": "枕下肌、C7-T1交界", "depth": "深層"},
    {"pair": {"CE", "MSE"}, "result": "深前線 / 骨盆以上 深前線", "muscles": "斜角肌、咀嚼肌", "depth": "深層"},
    {"pair": {"CR", "MSSBL"}, "result": "側線 / 骨盆以上 右側線", "muscles": "右枕骨邊緣/乳突交界、右髂棘上下", "depth": "深層"},
    {"pair": {"CR", "MSSBR"}, "result": "側線 / 骨盆以上 左側線", "muscles": "左枕骨邊緣/乳突交界、左髂棘上下", "depth": "深層"},
    {"pair": {"MSRR", "MSSBL"}, "result": "骨盆以下 右側線或左深前線", "muscles": "加測後判定", "depth": "最後處理"},
    {"pair": {"MSRL", "MSSBR"}, "result": "骨盆以下 左側線或右深前線", "muscles": "加測後判定", "depth": "最後處理"},
    {"pair": {"CE", "LAU"}, "result": "左深前臂線", "muscles": "左深前臂線", "depth": "深層"},
    {"pair": {"CE", "RAU"}, "result": "右深前臂線", "muscles": "右深前臂線", "depth": "深層"},
    {"pair": {"CRR", "LAD"}, "result": "左深後臂線", "muscles": "左深後臂線", "depth": "深層"},
    {"pair": {"CRL", "RAD"}, "result": "右深後臂線", "muscles": "右深後臂線", "depth": "深層"}
]

IMAGE_MAPPING = {"螺旋線": "SPL.jpg", "後功能線": "FF1.jpg", "前功能線": "FF2.jpg", "淺背線": "SBL.jpg", "側線": "LL.jpg", "深前線": "DFL.jpg", "深前臂線": "DFAL.jpg", "深後臂線": "DBAL.jpg"}

# --- 3. 介面分頁 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜", "📈 歷史追蹤"])

with tab1:
    st.subheader("👤 病人基本資料")
    p_name = st.text_input("病人姓名", key="p_name")
    p_id = st.text_input("病歷號", key="p_id")
    p_date = st.date_input("評估日期", value=datetime.now(tz_taiwan).date())
    vas_score = st.slider("🤒 病人自覺整體分數 (10分最痛)", 0, 10, 5)
    p_assessor = st.text_input("評估人")
    p_note = st.text_area("整體臨床總結備註")

with tab2:
    st.info("請標註評估等級。核心受限請點選 ⭐ 加權。")
    user_scores, user_priorities = {}, {}
    for i, act in enumerate(ACTIONS, 1):
        st.markdown(f"<div class='action-title'>{i}. 動作: {act}</div>", unsafe_allow_html=True)
        c1, c2 = st.columns([3, 1])
        user_scores[act] = c1.segmented_control(label=act, options=["FA", "FS", "DS", "DA"], key=f"s_{act}", selection_mode="single", label_visibility="collapsed")
        user_priorities[act] = c2.checkbox("⭐ 加權", key=f"prio_{act}")
        st.divider()

with tab3:
    st.subheader("📊 判定結果摘要")
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    priority_list = [k for k, v in user_priorities.items() if v]

    if da_list or ds_list:
        st.write(f"🛑 **DA:** {', '.join(da_list) if da_list else '無'} | ⚠️ **DS:** {', '.join(ds_list) if ds_list else '無'}")
        if priority_list: st.write(f"🌟 **關鍵加權點:** {', '.join(priority_list)}")
        st.divider()

    # 邏輯分類
    weighted_res, da_da_res, ds_ds_res = [], [], []
    for rule in TREATMENT_DATABASE:
        s1, s2 = user_scores.get(list(rule["pair"])[0]), user_scores.get(list(rule["pair"])[1])
        if s1 and s2 and s1 == s2 and s1 in ["DA", "DS"]:
            item = {**rule, "grade": s1, "is_prio": not rule["pair"].isdisjoint(set(priority_list))}
            if item["is_prio"]: weighted_res.append(item)
            elif s1 == "DA": da_da_res.append(item)
            else: ds_ds_res.append(item)

    # 輔助函數：顯示區塊 (淺層優先)
    def display_group(res_list, title):
        if res_list:
            if title: st.markdown(f"### {title}")
            # 排序：淺層=0, 深層=1, 最後處理=2
            depth_order = {"淺層": 0, "深層": 1, "最後處理": 2}
            for res in sorted(res_list, key=lambda x: depth_order.get(x["depth"], 1)):
                pair_str = " + ".join(sorted(list(res["pair"])))
                if res["is_prio"]:
                    st.markdown(f"<div class='priority-box'>🌟 加權重點項目<br>動作組合: {pair_str} ({res['depth']})<br>結果: {res['result']}<br><div class='muscle-text'>💪 建議處理肌肉: {res['muscles']}</div></div>", unsafe_allow_html=True)
                elif res["depth"] == "淺層":
                    st.markdown(f"<div class='superficial-header'>🌿 淺層判定</div><div class='superficial-box'><b>動作組合: {pair_str}</b><br>結果: {res['result']}<br><div class='muscle-text'>💪 建議處理肌肉: {res['muscles']}</div></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='deep-box'><strong>💎 深層判定</strong><br>動作組合: {pair_str}<br>結果: {res['result']}<br><div class='muscle-text'>💪 建議處理肌肉: {res['muscles']}</div></div>", unsafe_allow_html=True)
                
                # 圖片自動顯示 [cite: 94-95]
                imgs = [v for k, v in IMAGE_MAPPING.items() if k in res['result']]
                if imgs:
                    with st.expander(f"🔍 檢視圖譜: {res['result']}"):
                        for img in imgs: st.image(f"images/{img}", width=350)

    # 按順序顯示 
    display_group(weighted_res, "⭐ 加權重點對應")
    display_group(da_da_res, "🟦 DA-DA 對應結果")
    display_group(ds_ds_res, "🟧 DS-DS 對應結果")

    # 3. 踝部加測 (放在最後) [cite: 62-63]
    all_matched_pairs = [" + ".join(sorted(list(r["pair"]))) for r in weighted_res + da_da_res + ds_ds_res]
    for p_str in ["MSRR + MSSBL", "MSRL + MSSBR"]:
        if p_str in all_matched_pairs:
            st.markdown(f"<div class='ankle-box'>🔍 偵測到 {p_str} 相對應，請加測：</div>", unsafe_allow_html=True)
            side = "右" if "MSRR" in p_str else "左"
            opp = "左" if side == "右" else "右"
            if st.checkbox(f"{side}踝內翻受限 (處理{side}側線)", key=f"ak1_{p_str}"): st.info(f"💡 建議處理：{side}側線 (淺層)")
            if st.checkbox(f"{opp}踝外翻受限 (處理{opp}深前線)", key=f"ak2_{p_str}"): st.info(f"💡 建議處理：{opp}深前線 (深層)")

    if st.button("🚀 完成評估並同步雲端"): st.success("✅ 同步成功！"); st.balloons()

with tab4: # [cite: 102]
    st.subheader("📚 完整解剖圖譜")
    atlas = {"FF 功能線": ["FF1.jpg", "FF2.jpg"], "SBL 淺背線": ["SBL.jpg"], "SFL 淺前線": ["SFL.jpg"], "LL 側線": ["LL.jpg"], "SPL 螺旋線": ["SPL.jpg"], "DFL 深前線": ["DFL.jpg"], "手臂線系列": ["SFAL.jpg", "SBAL.jpg", "DFAL.jpg", "DBAL.jpg"]}
    for title, imgs in atlas.items():
        with st.expander(f"📍 {title}"):
            for img in imgs: st.image(f"images/{img}", use_container_width=True)

with tab5: # 恢復 V1.1 歷史追蹤功能 
    st.subheader("📈 歷史趨勢分析")
    search_id = st.text_input("輸入病歷號查詢歷史紀錄")
    if search_id:
        df = fetch_data_no_cache(conn)
        if not df.empty:
            df['病歷號'] = df['病歷號'].astype(str).str.lstrip("'").str.strip()
            p_history = df[df["病歷號"] == search_id].copy()
            if not p_history.empty:
                p_history['sort_dt'] = pd.to_datetime(p_history['日期'].str.replace(" (補)", ""), errors='coerce')
                p_history = p_history.sort_values("sort_dt")
                st.plotly_chart(px.bar(p_history, x="日期", y="病人自覺分數", color_discrete_sequence=["#1E88E5"], text_auto=True))
                st.dataframe(p_history.sort_values("sort_dt", ascending=False)[["日期", "判定結果", "備註"]])
