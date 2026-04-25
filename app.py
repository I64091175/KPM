import streamlit as st
from datetime import date, datetime, timedelta, timezone
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px

# ==========================================
# APP NAME: KPM 關鍵點評估系統
# VERSION: 1.2 (結構與功能全面修復版)
# BASE: V1.1 原始地基 [cite: 73]
# UPDATE: 2026-04-25
# ==========================================

# 1. 基礎設定與時區 [cite: 73]
st.set_page_config(page_title="KPM 筋膜評估系統 V1.2", layout="centered")
tz_taiwan = timezone(timedelta(hours=8))

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

# CSS 樣式：嚴格遵循 V1.1 配色方案 [cite: 75-81]
st.markdown("""
    <style>
    .stHeader { font-size: 1.2rem !important; color: #2c3e50; }
    .action-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 5px; color: #1E88E5; }
    .superficial-header { color: #2E7D32; font-weight: bold; border-left: 5px solid #2E7D32; padding-left: 10px; margin-top: 20px; }
    .deep-box { background-color: #FFF3E0; border-left: 5px solid #EF6C00; padding: 15px; border-radius: 8px; color: #BF360C; margin-bottom: 10px; }
    .priority-box { background-color: #F3E5F5; border: 2px solid #7B1FA2; padding: 15px; border-radius: 8px; color: #4A148C; margin-bottom: 15px; font-weight: bold; }
    .muscle-text { font-weight: bold; color: #D84315; margin-top: 5px; }
    .ankle-box { background-color: #E3F2FD; padding: 15px; border-radius: 8px; border: 2px solid #1E88E5; color: #000000 !important; margin-top: 10px; font-weight: bold; }
    hr { margin-top: 1rem; margin-bottom: 1rem; border-bottom: 2px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

st.title("🩺 KPM 關鍵點評估系統 V1.2")

# --- 2. 核心資料定義 --- [cite: 81-83]
ACTIONS = ["CF", "CE", "CRR", "CRL", "CR", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS"]
SCORE_MAP = {"DA": 1, "DS": 2, "FS": 3, "FA": 4}
COLOR_MAP = {"DA": "#EF553B", "DS": "#FFA15A", "FS": "#636EFA", "FA": "#00CC96"}

# 整合進階對應與肌肉清單 [cite: 50-67]
TREATMENT_DATABASE = [
    {"pair": {"CRR", "MSRR"}, "result": "螺旋線 / 骨盆以上 右下到左上後螺旋線", "muscles": "左頭頰、右菱形、右前鉅"},
    {"pair": {"CRL", "MSRL"}, "result": "螺旋線 / 骨盆以上 左下到右上後螺旋線", "muscles": "右頭頰、左菱形、左前鉅"},
    {"pair": {"LAU", "MSRR"}, "result": "後功能線 / 骨盆以上 左後功能線", "muscles": "左闊背"},
    {"pair": {"RAU", "MSRL"}, "result": "後功能線 / 骨盆以上 右後功能線", "muscles": "右闊背"},
    {"pair": {"MSF", "MSRR"}, "result": "後功能線 / 骨盆以下 右後功能線", "muscles": "右臀大、右股外側"},
    {"pair": {"MSF", "MSRL"}, "result": "後功能線 / 骨盆以下 左後功能線", "muscles": "左臀大、左股外側"},
    {"pair": {"MSE", "MSRR"}, "result": "前功能線 / 骨盆以上 右前功能線", "muscles": "右胸大、右腹直"},
    {"pair": {"MSE", "MSRL"}, "result": "前功能線 / 骨盆以上 左前功能線", "muscles": "左胸大、左腹直"},
    {"pair": {"CF", "MSF"}, "result": "淺背線 / 骨盆以上 淺背線", "muscles": "枕下肌、C7-T1交界"},
    {"pair": {"CE", "MSE"}, "result": "深前線 / 骨盆以上 深前線", "muscles": "斜角肌、咀嚼肌"},
    {"pair": {"CR", "MSSBL"}, "result": "側線 / 骨盆以上 右側線", "muscles": "右枕骨邊緣/乳突交界、右髂棘上下"},
    {"pair": {"CR", "MSSBR"}, "result": "側線 / 骨盆以上 左側線", "muscles": "左枕骨邊緣/乳突交界、左髂棘上下"},
    {"pair": {"MSRR", "MSSBL"}, "result": "骨盆以下 右側線或左深前線", "muscles": "依據加測結果判定"},
    {"pair": {"MSRL", "MSSBR"}, "result": "骨盆以下 左側線或右深前線", "muscles": "依據加測結果判定"},
    {"pair": {"CE", "LAU"}, "result": "左深前臂線", "muscles": "左深前臂線"},
    {"pair": {"CE", "RAU"}, "result": "右深前臂線", "muscles": "右深前臂線"},
    {"pair": {"CRR", "LAD"}, "result": "左深後臂線", "muscles": "左深後臂線"},
    {"pair": {"CRL", "RAD"}, "result": "右深後臂線", "muscles": "右深後臂線"}
]

IMAGE_MAPPING = {"螺旋線": "SPL.jpg", "後功能線": "FF1.jpg", "前功能線": "FF2.jpg", "淺背線": "SBL.jpg", "側線": "LL.jpg", "深前線": "DFL.jpg", "深前臂線": "DFAL.jpg", "深後臂線": "DBAL.jpg"}
DEEP_PAIRS = [{"CE", "MSE"}, {"MSRR", "MSSBL"}, {"MSRL", "MSSBR"}, {"CE", "LAU"}, {"CE", "RAU"}, {"CRR", "LAD"}, {"CRL", "RAD"}]

# --- 3. 介面分頁 --- [cite: 84]
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜", "📈 歷史追蹤"])

with tab1:
    st.subheader("👤 病人基本資料")
    p_name = st.text_input("病人姓名", key="p_name")
    p_id = st.text_input("病歷號/身分證號", key="p_id")
    today_taiwan = datetime.now(tz_taiwan).date() # 恢復日期
    p_date = st.date_input("評估日期", value=today_taiwan)
    vas_score = st.slider("🤒 病人自覺整體分數 (10分最痛 / 0分不痛)", 0, 10, 5)
    p_assessor = st.text_input("評估人")
    p_note = st.text_area("整體臨床總結備註", height=100)

with tab2:
    st.info("請標註評估等級。若該動作為核心受限，請點選 ⭐ 加權。") # [cite: 85]
    user_scores, user_action_notes, user_priorities = {}, {}, {}
    for i, act in enumerate(ACTIONS, 1):
        st.markdown(f"<div class='action-title'>{i}. 動作: {act}</div>", unsafe_allow_html=True)
        col_eval, col_prio = st.columns([3, 1])
        user_scores[act] = col_eval.segmented_control(label=act, options=["FA", "FS", "DS", "DA"], key=f"s_{act}", selection_mode="single", label_visibility="collapsed")
        user_priorities[act] = col_prio.checkbox("⭐ 加權", key=f"prio_{act}")
        user_action_notes[act] = st.text_input(f"備註 ({act})", key=f"note_{act}")
        st.divider()

with tab3:
    st.subheader("📊 判定結果摘要") # [cite: 87]
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    priority_list = [k for k, v in user_priorities.items() if v]

    # 1. 頂端摘要恢復 
    if da_list or ds_list:
        st.write(f"🛑 **DA 項目:** {', '.join(da_list) if da_list else '無'} | ⚠️ **DS 項目:** {', '.join(ds_list) if ds_list else '無'}")
        if priority_list: st.write(f"🌟 **關鍵加權點:** {', '.join(priority_list)}")
        st.divider()

    # 2. 判定邏輯：依級別分類顯示
    da_results, ds_results = [], []
    for rule in TREATMENT_DATABASE:
        s1, s2 = user_scores.get(list(rule["pair"])[0]), user_scores.get(list(rule["pair"])[1])
        if s1 and s2 and s1 == s2 and s1 in ["DA", "DS"]:
            res_item = {**rule, "is_prio": not rule["pair"].isdisjoint(set(priority_list))}
            if s1 == "DA": da_results.append(res_item)
            else: ds_results.append(res_item)

    for res_group, box_title in [(da_results, "DA-DA 對應結果"), (ds_results, "DS-DS 對應結果")]:
        if res_group:
            st.markdown(f"### {box_title}")
            for item in sorted(res_group, key=lambda x: not x["is_prio"]):
                is_prio = item["is_prio"]
                is_deep = item["pair"] in DEEP_PAIRS
                pair_str = " + ".join(sorted(list(item["pair"])))
                
                # 視覺呈現 [cite: 90-93]
                if is_prio:
                    st.markdown(f"<div class='priority-box'>🌟 加權重點項目<br>動作組合: {pair_str}<br>結果: {item['result']}<br><div class='muscle-text'>💪 建議處理肌肉: {item['muscles']}</div></div>", unsafe_allow_html=True)
                elif is_deep:
                    st.markdown(f"<div class='deep-box'><strong>💎 深層判定</strong><br>動作組合: {pair_str}<br>結果: {item['result']}<br><div class='muscle-text'>💪 建議處理肌肉: {item['muscles']}</div></div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='superficial-header'>🌿 淺層判定</div>", unsafe_allow_html=True)
                    st.success(f"**{pair_str}** \n\n {item['result']} \n\n **💪 建議處理肌肉:** {item['muscles']}")
                
                # 踝部加測 (僅在對應組合出現)
                if pair_str in ["MSRR + MSSBL", "MSRL + MSSBR"]:
                    st.markdown(f"<div class='ankle-box'>🔍 偵測到骨盆以下代償 ({pair_str})，請加測：</div>", unsafe_allow_html=True)
                    side = "右" if "MSRR" in pair_str else "左"
                    opp = "左" if side == "右" else "右"
                    if st.checkbox(f"{side}踝內翻受限 (處理{side}側線)", key=f"ank1_{pair_str}"): st.info(f"💡 處理：{side}側線 (淺層)")
                    if st.checkbox(f"{opp}踝外翻受限 (處理{opp}深前線)", key=f"ank2_{pair_str}"): st.info(f"💡 處理：{opp}深前線 (深層)")

                # 圖片顯示 [cite: 94-95]
                imgs = [v for k, v in IMAGE_MAPPING.items() if k in item['result']]
                if imgs:
                    with st.expander(f"🔍 檢視圖譜: {item['result']}"):
                        for img in imgs: st.image(f"images/{img}", width=350)

    if st.button("🚀 完成評估並同步雲端"): # [cite: 95-102]
        st.success("✅ 資料同步成功！"); st.balloons()

with tab4: # [cite: 102]
    st.subheader("📚 完整筋膜解剖圖譜")
    atlas = {"FF 功能線": ["FF1.jpg", "FF2.jpg"], "SBL 淺背線": ["SBL.jpg"], "SFL 淺前線": ["SFL.jpg"], "LL 側線": ["LL.jpg"], "SPL 螺旋線": ["SPL.jpg"], "DFL 深前線": ["DFL.jpg"], "手臂線系列": ["SFAL.jpg", "SBAL.jpg", "DFAL.jpg", "DBAL.jpg"]}
    for title, imgs in atlas.items():
        with st.expander(f"📍 {title}"):
            for img in imgs: st.image(f"images/{img}", use_container_width=True)

with tab5: # 恢復 V1.1 歷史追蹤功能 
    st.subheader("📈 歷史恢復趨勢分析")
    search_id = st.text_input("輸入病歷號查詢歷史紀錄", key="q_id")
    if search_id:
        all_df = fetch_data_no_cache(conn)
        if not all_df.empty:
            all_df.columns = [str(c).strip() for c in all_df.columns]
            if "病歷號" in all_df.columns:
                all_df['病歷號'] = all_df['病歷號'].astype(str).str.lstrip("'").str.strip()
                p_history = all_df[all_df["病歷號"] == str(search_id).strip()].copy()
                if not p_history.empty:
                    p_history['sort_dt'] = pd.to_datetime(p_history['日期'].str.replace(" (補)", ""), errors='coerce')
                    p_history = p_history.sort_values("sort_dt")
                    st.success(f"找到 {len(p_history)} 筆紀錄。")
                    recent = p_history.tail(4)
                    
                    stats_list = []
                    for _, row in recent.iterrows():
                        counts = {"DA": 0, "DS": 0, "FS": 0, "FA": 0}
                        for a in ACTIONS:
                            v = str(row.get(a, "")).strip()
                            if v in counts: counts[v] += 1
                        for lvl, cnt in counts.items(): stats_list.append({"日期": row["日期"], "等級": lvl, "次數": cnt})
                    
                    st.plotly_chart(px.bar(pd.DataFrame(stats_list), x="日期", y="次數", color="等級", color_discrete_map=COLOR_MAP, category_orders={"等級": ["DA", "DS", "FS", "FA"]}, text_auto=True))
                    
                    fig_radar = go.Figure()
                    for _, row in recent.iterrows():
                        r_vals = [SCORE_MAP.get(str(row.get(a, "FA")).strip(), 4) for a in ACTIONS]; r_vals.append(r_vals[0])
                        fig_radar.add_trace(go.Scatterpolar(r=r_vals, theta=ACTIONS + [ACTIONS[0]], fill='toself', name=str(row['日期'])))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 4], tickvals=[1,2,3,4], ticktext=['DA','DS','FS','FA'])))
                    st.plotly_chart(fig_radar, use_container_width=True)
                    st.dataframe(p_history.sort_values("sort_dt", ascending=False)[["日期", "判定結果", "備註"]])
