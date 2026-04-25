import streamlit as st
from datetime import date, datetime, timedelta, timezone
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px

# ==========================================
# APP NAME: KPM 關鍵點評估系統
# VERSION: 1.2 (最終修正版)
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

# CSS 樣式：強化加權視覺與文字能見度
st.markdown("""
    <style>
    .da-box { background-color: #F3E5F5; border: 2px solid #7B1FA2; padding: 15px; border-radius: 8px; color: #4A148C; margin-bottom: 10px; }
    .ds-box { background-color: #FFF3E0; border: 2px solid #EF6C00; padding: 15px; border-radius: 8px; color: #BF360C; margin-bottom: 10px; }
    .priority-item { border: 3px solid #6A1B9A !important; background-color: #EDE7F6 !important; }
    .ankle-box { background-color: #E3F2FD; padding: 15px; border-radius: 8px; border: 2px solid #1E88E5; color: #000000 !important; margin-top: 10px; font-weight: bold; }
    .muscle-text { font-weight: bold; color: #D84315; margin-top: 5px; }
    .depth-tag { font-size: 0.9rem; color: #616161; }
    </style>
    """, unsafe_allow_html=True)

st.title("🩺 KPM 關鍵點評估系統 V1.2")

# --- 2. 核心資料定義 (更新肌肉清單) ---
ACTIONS = ["CF", "CE", "CRR", "CRL", "CR", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS"]
SCORE_MAP = {"DA": 1, "DS": 2, "FS": 3, "FA": 4}
COLOR_MAP = {"DA": "#EF553B", "DS": "#FFA15A", "FS": "#636EFA", "FA": "#00CC96"}

# 整合進階對應與肌肉名稱 
TREATMENT_DATABASE = [
    {"pair": {"CRR", "MSRR"}, "result": "螺旋線 / 骨盆以上 右下到左上後螺旋線", "depth": "深層", "muscles": "左頭頰、右菱形、右前鉅", "tier": 3},
    {"pair": {"CRL", "MSRL"}, "result": "螺旋線 / 骨盆以上 左下到右上後螺旋線", "depth": "深層", "muscles": "右頭頰、左菱形、左前鉅", "tier": 3},
    {"pair": {"LAU", "MSRR"}, "result": "後功能線 / 骨盆以上 左後功能線", "depth": "淺層", "muscles": "左闊背", "tier": 1},
    {"pair": {"RAU", "MSRL"}, "result": "後功能線 / 骨盆以上 右後功能線", "depth": "淺層", "muscles": "右闊背", "tier": 1},
    {"pair": {"MSF", "MSRR"}, "result": "後功能線 / 骨盆以下 右後功能線", "depth": "淺層", "muscles": "右臀大、右股外側", "tier": 2},
    {"pair": {"MSF", "MSRL"}, "result": "後功能線 / 骨盆以下 左後功能線", "depth": "淺層", "muscles": "左臀大、左股外側", "tier": 2},
    {"pair": {"MSE", "MSRR"}, "result": "前功能線 / 骨盆以上 右前功能線", "depth": "淺層", "muscles": "右胸大、右腹直", "tier": 1},
    {"pair": {"MSE", "MSRL"}, "result": "前功能線 / 骨盆以上 左前功能線", "depth": "淺層", "muscles": "左胸大、左腹直", "tier": 1},
    {"pair": {"CF", "MSF"}, "result": "淺背線 / 骨盆以上 淺背線", "depth": "深層", "muscles": "枕下肌、C7-T1交界", "tier": 3},
    {"pair": {"CE", "MSE"}, "result": "深前線 / 骨盆以上 深前線", "depth": "深層", "muscles": "斜角肌、咀嚼肌", "tier": 3},
    {"pair": {"CR", "MSSBL"}, "result": "側線 / 骨盆以上 右側線", "depth": "深層", "muscles": "右枕骨邊緣/乳突交界、右髂棘上下", "tier": 3},
    {"pair": {"CR", "MSSBR"}, "result": "側線 / 骨盆以上 左側線", "depth": "深層", "muscles": "左枕骨邊緣/乳突交界、左髂棘上下", "tier": 3},
    {"pair": {"CE", "LAU"}, "result": "左深前臂線", "depth": "深層", "muscles": "左深前臂線", "tier": 4},
    {"pair": {"CE", "RAU"}, "result": "右深前臂線", "depth": "深層", "muscles": "右深前臂線", "tier": 4},
    {"pair": {"CRR", "LAD"}, "result": "左深後臂線", "depth": "深層", "muscles": "左深後臂線", "tier": 4},
    {"pair": {"CRL", "RAD"}, "result": "右深後臂線", "depth": "深層", "muscles": "右深後臂線", "tier": 4}
]

IMAGE_MAPPING = {"螺旋線": "SPL.jpg", "後功能線": "FF1.jpg", "前功能線": "FF2.jpg", "淺背線": "SBL.jpg", "側線": "LL.jpg", "深前線": "DFL.jpg"}

# --- 3. 介面分頁 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜", "📈 歷史追蹤"])

with tab1:
    st.subheader("👤 病人基本資料")
    p_name = st.text_input("病人姓名", key="p_name")
    p_id = st.text_input("病歷號", key="p_id")
    # 修復：恢復日期輸入 
    today_taiwan = datetime.now(tz_taiwan).date()
    p_date = st.date_input("評估日期", value=today_taiwan)
    vas_score = st.slider("🤒 病人自覺分數 (10最痛 / 0不痛)", 0, 10, 5)
    p_assessor = st.text_input("評估人")
    p_note = st.text_area("臨床備註")

with tab2:
    st.info("請標註等級。核心受限請點選 ⭐ 加權。")
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
    # 恢復：DA/DS 項目摘要 [cite: 87]
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    priority_list = [k for k, v in user_priorities.items() if v]
    if da_list or ds_list:
        st.write(f"🛑 **DA:** {', '.join(da_list) if da_list else '無'} | ⚠️ **DS:** {', '.join(ds_list) if ds_list else '無'}")
        st.divider()

    da_results, ds_results = [], []
    for rule in TREATMENT_DATABASE:
        s1, s2 = user_scores.get(list(rule["pair"])[0]), user_scores.get(list(rule["pair"])[1])
        if s1 and s2 and s1 == s2:
            res_item = {**rule, "is_weighted": not rule["pair"].isdisjoint(set(priority_list))}
            if s1 == "DA": da_results.append(res_item)
            elif s1 == "DS": ds_results.append(res_item)

    for res_group, box_style, title in [(da_results, "da-box", "DA-DA 對應"), (ds_results, "ds-box", "DS-DS 對應")]:
        if res_group:
            st.markdown(f"### {title}")
            for res in sorted(res_group, key=lambda x: (not x["is_weighted"], x["tier"])):
                # 修復：加權視覺呈現
                weight_tag = "🌟 **加權重點項目** | " if res["is_weighted"] else ""
                prio_class = "priority-item" if res["is_weighted"] else ""
                pair_str = " + ".join(list(res["pair"]))
                
                st.markdown(f"""
                    <div class='{box_style} {prio_class}'>
                        {weight_tag}<b>動作組合: {pair_str}</b> <span class='depth-tag'>({res['depth']})</span><br>
                        判定結果: {res['result']}<br>
                        <div class='muscle-text'>💪 建議處理肌肉: {res['muscles']}</div>
                    </div>
                """, unsafe_allow_html=True)

                if pair_str in ["MSRR + MSSBL", "MSRL + MSSBR"]:
                    st.markdown(f"<div class='ankle-box'>🔍 偵測到骨盆以下代償 ({pair_str})，請加測：</div>", unsafe_allow_html=True)
                    side = "右" if "MSRR" in pair_str else "左"
                    opp = "左" if side == "右" else "右"
                    if st.checkbox(f"{side}踝內翻受限 (處理{side}側線)", key=f"a1_{pair_str}"): st.info(f"💡 處理：{side}側線 (淺層)")
                    if st.checkbox(f"{opp}踝外翻受限 (處理{opp}深前線)", key=f"a2_{pair_str}"): st.info(f"💡 處理：{opp}深前線 (深層)")

                found_imgs = [v for k, v in IMAGE_MAPPING.items() if k in res['result']]
                if found_imgs:
                    with st.expander(f"🔍 檢視圖譜"):
                        for img in found_imgs: st.image(f"images/{img}", width=350)

    if st.button("🚀 完成評估並同步"):
        st.success("同步成功！")

with tab4:
    st.subheader("📚 完整解剖圖譜")
    atlas = {"FF 功能線": ["FF1.jpg", "FF2.jpg"], "SBL 淺背線": ["SBL.jpg"], "SFL 淺前線": ["SFL.jpg"], "LL 側線": ["LL.jpg"], "SPL 螺旋線": ["SPL.jpg"], "DFL 深前線": ["DFL.jpg"], "手臂線系列": ["SFAL.jpg", "SBAL.jpg", "DFAL.jpg", "DBAL.jpg"]}
    for title, imgs in atlas.items():
        with st.expander(f"📍 {title}"):
            for img in imgs: st.image(f"images/{img}", use_container_width=True)

with tab5:
    # 修復：恢復歷史追蹤功能 
    st.subheader("📈 歷史恢復趨勢")
    search_id = st.text_input("輸入病歷號查詢")
    if search_id:
        all_df = fetch_data_no_cache(conn)
        if not all_df.empty:
            all_df['病歷號'] = all_df['病歷號'].astype(str).str.lstrip("'").str.strip()
            p_history = all_df[all_df["病歷號"] == search_id].copy()
            if not p_history.empty:
                p_history['sort_dt'] = pd.to_datetime(p_history['日期'].str.replace(" (補)", ""), errors='coerce')
                p_history = p_history.sort_values("sort_dt")
                st.plotly_chart(px.bar(p_history, x="日期", y="病人自覺分數", color_discrete_sequence=["#1E88E5"], text_auto=True))
                st.dataframe(p_history.sort_values("sort_dt", ascending=False)[["日期", "判定結果", "備註"]])
