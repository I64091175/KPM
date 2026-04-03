import streamlit as st
from datetime import date, datetime, timedelta, timezone
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px

# 1. 基礎設定
st.set_page_config(page_title="KPM 筋膜評估系統", layout="centered")

# 設定台灣時區
tz_taiwan = timezone(timedelta(hours=8))

def fetch_data_no_cache(_conn):
    try:
        return _conn.read(worksheet="Sheet1", ttl=0)
    except Exception as e:
        st.error(f"讀取資料庫失敗: {e}")
        return pd.DataFrame()

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

# --- 2. 資料定義 ---
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

# --- 3. 分頁設計 ---
tabs = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜", "📈 歷史追蹤"])

with tabs[0]:
    st.subheader("👤 病人基本資料")
    p_name = st.text_input("病人姓名", key="p_name")
    p_id = st.text_input("病歷號/身分證號", key="p_id")
    # 時區穩定化
    today_taiwan = datetime.now(tz_taiwan).date()
    p_date = st.date_input("評估日期", value=today_taiwan)
    p_assessor = st.text_input("評估人", key="p_assessor")
    p_note = st.text_area("整體臨床總結備註", height=100)

with tabs[1]:
    st.info("動作備註將自動串接至最後的備註欄")
    user_scores = {}
    user_action_notes = {}
    for i, act in enumerate(ACTIONS, 1):
        st.markdown(f"<div class='action-title'>{i}. 動作: {act}</div>", unsafe_allow_html=True)
        user_scores[act] = st.segmented_control(label=act, options=["FA", "FS", "DS", "DA"], key=f"s_{act}", selection_mode="single", label_visibility="collapsed")
        user_action_notes[act] = st.text_input(f"備註 ({act})", key=f"note_{act}")
        st.divider()

with tabs[2]:
    st.subheader("📊 判定結果摘要")
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    matches = [r for r in TREATMENT_DATABASE if r["pair"].issubset(set(da_list))] or [r for r in TREATMENT_DATABASE if r["pair"].issubset(set(ds_list))]

    if matches:
        for m in matches:
            if m["pair"] in DEEP_PAIRS:
                st.markdown(f"<div class='deep-box'><strong>💎 深層判定</strong><br>組合: {' + '.join(sorted(list(m['pair']))) }<br><br>結果: {m['result']}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='superficial-header'>🌿 淺層判定</div>", unsafe_allow_html=True)
                st.success(f"**{' + '.join(sorted(list(m['pair'])))}** \n\n {m['result']}")
            
            imgs = [v for k, v in IMAGE_MAPPING.items() if k in m['result']]
            if imgs:
                with st.expander("🔍 檢視對應筋膜圖 (50%)"):
                    for img in imgs:
                        l, mid, r = st.columns([1, 2, 1])
                        mid.image(f"images/{img}", use_container_width=True)
    else: st.info("目前組合尚未定義對應筋膜線。")

    st.divider()
    if st.button("🚀 完成評估並同步雲端"):
        if not p_name or not p_id: st.error("請輸入姓名與病歷號！")
        else:
            try:
                # 備註合併
                action_detail_list = [f"{act}:{user_action_notes[act].strip()}" for act in ACTIONS if user_action_notes[act].strip()]
                combined_details = "/".join(action_detail_list)
                final_combined_note = f"{p_note} | 詳細: {combined_details}" if p_note and combined_details else (p_note or combined_details)

                # 時間邏輯
                now_taiwan = datetime.now(tz_taiwan)
                final_datetime_str = now_taiwan.strftime("%Y-%m-%d %H:%M") if p_date >= now_taiwan.date() else f"{p_date} (補)"

                # 同步
                record = {"日期": final_datetime_str, "評估人": p_assessor, "病人姓名": p_name, "病歷號": f"'{p_id}", "DA": ", ".join(da_list), "DS": ", ".join(ds_list), "判定結果": " / ".join([m['result'] for m in matches]), "備註": final_combined_note}
                record.update(user_scores)
                df_old = fetch_data_no_cache(conn)
                df_final = pd.concat([df_old, pd.DataFrame([record])], ignore_index=True)
                conn.update(worksheet="Sheet1", data=df_final)
                st.success(f"✅ 已同步！時間：{final_datetime_str}"); st.balloons()
            except Exception as e: st.error(f"失敗：{e}")

with tabs[3]:
    st.subheader("📚 完整筋膜解剖圖譜")
    atlas = {"FF 功能線 (前+後)": ["FF1.jpg", "FF2.jpg"], "SBL 淺背線": ["SBL.jpg"], "SFL 淺前線": ["SFL.jpg"], "LL 側線": ["LL.jpg"], "SPL 螺旋線": ["SPL.jpg"], "DFL 深前線": ["DFL.jpg"], "SFAL 淺前臂線": ["SFAL.jpg"], "SBAL 淺後臂線": ["SBAL.jpg"], "DFAL 深前臂線": ["DFAL.jpg"], "DBAL 深後臂線": ["DBAL.jpg"]}
    for title, imgs in atlas.items():
        with st.expander(f"📍 {title}"):
            for img in imgs: st.image(f"images/{img}", use_container_width=True)

with tabs[4]:
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
                    # 修正排序邏輯
                    p_history['sort_date'] = pd.to_datetime(p_history['日期'].str.replace(" (補)", "", regex=False), errors='coerce')
                    p_history = p_history.sort_values("sort_date")
                    
                    count = len(p_history)
                    show_n = min(count, 4)
                    st.success(f"找到 {count} 筆紀錄，顯示最近 {show_n} 次對比：")
                    
                    recent = p_history.tail(4)
                    # 統計圖
                    stats_list = []
                    for _, row in recent.iterrows():
                        counts = {"DA": 0, "DS": 0, "FS": 0, "FA": 0}
                        for a in ACTIONS:
                            v = str(row.get(a, "")).strip()
                            if v in counts: counts[v] += 1
                        for lvl, cnt in counts.items(): stats_list.append({"日期": row["日期"], "等級": lvl, "次數": cnt})
                    
                    fig_bar = px.bar(pd.DataFrame(stats_list), x="日期", y="次數", color="等級", color_discrete_map=COLOR_MAP, category_orders={"等級": ["DA", "DS", "FS", "FA"]}, text_auto=True)
                    st.plotly_chart(fig_bar, use_container_width=True)

                    # 雷達圖
                    fig_radar = go.Figure()
                    for _, row in recent.iterrows():
                        r_vals = [SCORE_MAP.get(str(row.get(a, "FA")).strip(), 4) for a in ACTIONS]; r_vals.append(r_vals[0])
                        fig_radar.add_trace(go.Scatterpolar(r=r_vals, theta=ACTIONS + [ACTIONS[0]], fill='toself', name=str(row['日期'])))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 4], tickvals=[1,2,3,4], ticktext=['DA','DS','FS','FA'])))
                    st.plotly_chart(fig_radar, use_container_width=True)

                    # ✅ 修正 KeyError 行：先排序完，再選欄位顯示
                    p_display = p_history.sort_values("sort_date", ascending=False)
                    st.dataframe(p_display[["日期", "判定結果", "備註"]])
                else: st.warning("查無資料。")
