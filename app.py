# ==========================================
# APP NAME: KPM 關鍵點評估系統
# VERSION: 1.1 (流量防護最終版)
# UPDATE: 2026-04-05
# FEATURES: 
#   - 支援台灣時區 (UTC+8)
#   - 備註自動合併 (動作:內容/動作:內容)
#   - 歷史紀錄排序修復 (支援 "(補)" 字樣)
#   - 10 分鐘快取保護 (TTL=600)
# ==========================================

import streamlit as st
from datetime import date, datetime, timedelta, timezone
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px

# 1. 基礎設定與時區
st.set_page_config(page_title="KPM 筋膜評估系統", layout="centered")
tz_taiwan = timezone(timedelta(hours=8))

# 2. 快取讀取邏輯 (TTL=600 降低 API 負載)
@st.cache_data(ttl=600)
def fetch_data_cached(_conn):
    return _conn.read(worksheet="Sheet1", ttl=0)

conn = st.connection("gsheets", type=GSheetsConnection)

# CSS 樣式
st.markdown("""
    <style>
    .stHeader { font-size: 1.2rem !important; color: #2c3e50; }
    .action-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 5px; color: #1E88E5; }
    .superficial-header { color: #2E7D32; font-weight: bold; border-left: 5px solid #2E7D32; padding-left: 10px; margin-top: 20px; }
    .deep-box {
        background-color: #FFF3E0;
        border-left: 5px solid #EF6C00;
        padding: 15px;
        border-radius: 8px;
        color: #BF360C;
        margin-bottom: 15px;
    }
    hr { margin-top: 1rem; margin-bottom: 1rem; border-bottom: 2px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

st.title("🩺 KPM 關鍵點評估系統")

# --- 核心參數 ---
ACTIONS = ["CF", "CE", "CRR", "CRL", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS", "CR"]
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

IMAGE_MAPPING = {
    "螺旋線": "SPL.jpg", "後功能線": "FF1.jpg", "前功能線": "FF2.jpg",
    "淺背線": "SBL.jpg", "淺前線": "SFL.jpg", "側線": "LL.jpg",
    "深前線": "DFL.jpg", "深前臂線": "DFAL.jpg", "深後臂線": "DBAL.jpg",
    "淺前臂線": "SFAL.jpg", "淺後臂線": "SBAL.jpg"
}

DEEP_PAIRS = [{"CE", "MSE"}, {"MSRR", "MSSBL"}, {"MSRL", "MSSBR"}, {"CE", "LAU"}, {"CE", "RAU"}, {"CRR", "LAD"}, {"CRL", "RAD"}]

# --- 分頁 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜", "📈 歷史追蹤"])

with tab1:
    p_name = st.text_input("病人姓名", key="p_name")
    p_id = st.text_input("病歷號/身分證號", key="p_id", placeholder="例如: 00123")
    today_taiwan = datetime.now(tz_taiwan).date()
    p_date = st.date_input("評估日期", value=today_taiwan)
    p_assessor = st.text_input("評估人", key="p_assessor")
    p_note = st.text_area("整體臨床總結備註", height=100)

with tab2:
    user_scores = {}
    user_action_notes = {}
    for i, act in enumerate(ACTIONS, 1):
        st.markdown(f"<div class='action-title'>{i}. 動作: {act}</div>", unsafe_allow_html=True)
        user_scores[act] = st.segmented_control(label=act, options=["FA", "FS", "DS", "DA"], key=f"s_{act}", selection_mode="single", label_visibility="collapsed")
        user_action_notes[act] = st.text_input(f"備註 ({act})", key=f"note_{act}")
        st.divider()

with tab3:
    st.subheader("📊 判定結果摘要")
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    matches = [r for r in TREATMENT_DATABASE if r["pair"].issubset(set(da_list))] or [r for r in TREATMENT_DATABASE if r["pair"].issubset(set(ds_list))]

    if matches:
        for m in matches:
            if m["pair"] in DEEP_PAIRS:
                st.markdown(f"<div class='deep-box'><strong>💎 深層判定</strong><br>結果: {m['result']}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='superficial-header'>🌿 淺層判定</div>", unsafe_allow_html=True)
                st.success(f"**{' + '.join(sorted(list(m['pair'])))}** \n\n {m['result']}")
            
            imgs = [v for k, v in IMAGE_MAPPING.items() if k in m['result']]
            if imgs:
                with st.expander("🔍 檢視圖譜 (50%)"):
                    for img in imgs:
                        l, mid, r = st.columns([1, 2, 1])
                        mid.image(f"images/{img}", use_container_width=True)
    else: st.info("目前點選組合尚未觸發判定規則。")

    st.divider()
    if st.button("🚀 完成評估並同步雲端"):
        if not p_name or not p_id:
            st.error("請輸入姓名與病歷號！")
        else:
            with st.spinner("同步中..."):
                try:
                    action_detail_list = [f"{act}:{user_action_notes[act].strip()}" for act in ACTIONS if user_action_notes[act].strip()]
                    combined_details = "/".join(action_detail_list)
                    final_note = f"{p_note} | 詳細: {combined_details}" if p_note and combined_details else (p_note or combined_details)

                    now_taiwan = datetime.now(tz_taiwan)
                    time_str = now_taiwan.strftime("%Y-%m-%d %H:%M") if p_date >= now_taiwan.date() else f"{p_date} (補)"

                    record = {"日期": time_str, "評估人": p_assessor, "病人姓名": p_name, "病歷號": f"'{p_id}", "判定結果": " / ".join([m['result'] for m in matches]), "備註": final_note}
                    record.update(user_scores)
                    
                    df_old = conn.read(worksheet="Sheet1", ttl=0) # 寫入必抓最新
                    df_final = pd.concat([df_old, pd.DataFrame([record])], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=df_final)
                    
                    st.cache_data.clear() # 更新完清除快取
                    st.success(f"✅ 同步成功！({time_str})"); st.balloons()
                except Exception as e:
                    st.error(f"同步失敗 (API 繁忙，請稍候 1 分鐘): {e}")

with tab4:
    st.subheader("📚 完整筋膜解譜圖")
    atlas = {"FF 功能線 (前+後)": ["FF1.jpg", "FF2.jpg"], "SBL 淺背線": ["SBL.jpg"], "SFL 淺前線": ["SFL.jpg"], "LL 側線": ["LL.jpg"], "SPL 螺旋線": ["SPL.jpg"], "DFL 深前線": ["DFL.jpg"], "SFAL 淺前臂線": ["SFAL.jpg"], "SBAL 淺後臂線": ["SBAL.jpg"], "DFAL 深前臂線": ["DFAL.jpg"], "DBAL 深後臂線": ["DBAL.jpg"]}
    for title, imgs in atlas.items():
        with st.expander(f"📍 {title}"):
            for img in imgs: st.image(f"images/{img}", use_container_width=True)

with tab5:
    st.subheader("📈 歷史恢復趨勢分析")
    if st.button("🔄 重新整理資料庫"):
        st.cache_data.clear(); st.rerun()

    search_id = st.text_input("輸入病歷號查詢歷史紀錄", key="q_id")
    if search_id:
        all_df = fetch_data_cached(conn)
        if not all_df.empty:
            all_df.columns = [str(c).strip() for c in all_df.columns]
            if "病歷號" in all_df.columns:
                all_df['病歷號'] = all_df['病歷號'].astype(str).str.lstrip("'").str.strip()
                p_history = all_df[all_df["病歷號"] == str(search_id).strip()].copy()
                
                if not p_history.empty:
                    p_history['sort_date'] = pd.to_datetime(p_history['日期'].str.replace(" (補)", "", regex=False), errors='coerce')
                    p_history = p_history.sort_values("sort_date")
                    
                    st.success(f"找到 {len(p_history)} 筆紀錄。")
                    recent = p_history.tail(4)
                    
                    # 統計圖
                    stats_list = []
                    for _, row in recent.iterrows():
                        counts = {"DA": 0, "DS": 0, "FS": 0, "FA": 0}
                        for a in ACTIONS:
                            v = str(row.get(a, "")).strip()
                            if v in counts: counts[v] += 1
                        for lvl, cnt in counts.items(): stats_list.append({"日期": row["日期"], "等級": lvl, "次數": cnt})
                    
                    st.plotly_chart(px.bar(pd.DataFrame(stats_list), x="日期", y="次數", color="等級", color_discrete_map=COLOR_MAP, category_orders={"等級": ["DA", "DS", "FS", "FA"]}, text_auto=True), use_container_width=True)

                    # 雷達圖
                    fig_radar = go.Figure()
                    for _, row in recent.iterrows():
                        r_vals = [SCORE_MAP.get(str(row.get(a, "FA")).strip(), 4) for a in ACTIONS]; r_vals.append(r_vals[0])
                        fig_radar.add_trace(go.Scatterpolar(r=r_vals, theta=ACTIONS + [ACTIONS[0]], fill='toself', name=str(row['日期'])))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 4], tickvals=[1,2,3,4], ticktext=['DA','DS','FS','FA'])))
                    st.plotly_chart(fig_radar, use_container_width=True)

                    st.dataframe(p_history.sort_values("sort_date", ascending=False)[["日期", "判定結果", "備註"]])
