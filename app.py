import streamlit as st
from datetime import date, datetime
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px

# 1. 基礎設定
st.set_page_config(page_title="KPM 筋膜評估系統", layout="centered")

def fetch_data_no_cache(_conn):
    try:
        return _conn.read(worksheet="Sheet1", ttl=0)
    except Exception as e:
        st.error(f"讀取資料庫失敗: {e}")
        return pd.DataFrame()

conn = st.connection("gsheets", type=GSheetsConnection)

# CSS 樣式加強：區分深淺層顏色
st.markdown("""
    <style>
    .stHeader { font-size: 1.2rem !important; color: #2c3e50; }
    .action-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 5px; color: #1E88E5; }
    .superficial-header { color: #2E7D32; font-weight: bold; border-left: 5px solid #2E7D32; padding-left: 10px; margin-top: 20px; }
    .deep-header { color: #E65100; font-weight: bold; border-left: 5px solid #E65100; padding-left: 10px; margin-top: 20px; }
    /* 自定義深層判定警示盒 */
    .deep-box {
        background-color: #FFF3E0;
        border-left: 5px solid #EF6C00;
        padding: 15px;
        border-radius: 5px;
        color: #BF360C;
        margin-bottom: 10px;
    }
    hr { margin-top: 1rem; margin-bottom: 1rem; border-bottom: 2px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

st.title("🩺 KPM 關鍵點評估系統")

# --- 2. 核心資料定義 ---
ACTIONS = ["CF", "CE", "CRR", "CRL", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS", "CR"]
SCORE_MAP = {"DA": 1, "DS": 2, "FS": 3, "FA": 4}
COLOR_MAP = {"DA": "#EF553B", "DS": "#FFA15A", "FS": "#636EFA", "FA": "#00CC96"}

TREATMENT_DATABASE = [
    {"pair": {"CRR", "MSRR"}, "result": "骨盆以上 右下到左上後螺旋線"},
    {"pair": {"CRL", "MSRL"}, "result": "骨盆以上 左下到右上後螺旋線"},
    {"pair": {"LAU", "MSRR"}, "result": "骨盆以上 左後功能線"},
    {"pair": {"RAU", "MSRL"}, "result": "骨盆以上 右後功能線"},
    {"pair": {"MSF", "MSRR"}, "result": "骨盆以下 右後功能線"},
    {"pair": {"MSF", "MSRL"}, "result": "骨盆以下 左後功能線"},
    {"pair": {"MSE", "MSRR"}, "result": "骨盆以上 右前功能線"},
    {"pair": {"MSE", "MSRL"}, "result": "骨盆以上 左前功能線"},
    {"pair": {"CF", "MSF"}, "result": "骨盆以上 淺背線"},
    {"pair": {"CE", "MSE"}, "result": "骨盆以上 深前線"},
    {"pair": {"CR", "MSSBL"}, "result": "骨盆以上 右側線"},
    {"pair": {"CR", "MSSBR"}, "result": "骨盆以上 左側線"},
    {"pair": {"MSRR", "MSSBL"}, "result": "骨盆以下 右側線或左深前線"},
    {"pair": {"MSRL", "MSSBR"}, "result": "骨盆以下 左側線或右深前線"},
    {"pair": {"CE", "LAU"}, "result": "左深前臂線"},
    {"pair": {"CE", "RAU"}, "result": "右深前臂線"},
    {"pair": {"CRR", "LAD"}, "result": "左深後臂線"},
    {"pair": {"CRL", "RAD"}, "result": "右深後臂線"},
]

IMAGE_MAPPING = {
    "螺旋線": "SPL.jpg", "後功能線": "FF1.jpg", "前功能線": "FF2.jpg",
    "淺背線": "SBL.jpg", "淺前線": "SFL.jpg", "側線": "LL.jpg",
    "深前線": "DFL.jpg", "深前臂線": "DFAL.jpg", "深後臂線": "DBAL.jpg",
    "淺前臂線": "SFAL.jpg", "淺後臂線": "SBAL.jpg"
}

DEEP_PAIRS = [{"CE", "MSE"}, {"MSRR", "MSSBL"}, {"MSRL", "MSSBR"}, {"CE", "LAU"}, {"CE", "RAU"}, {"CRR", "LAD"}, {"CRL", "RAD"}]

# --- 3. 介面分頁 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜", "📈 歷史追蹤"])

with tab1:
    st.subheader("👤 基本資料")
    p_name = st.text_input("病人姓名", key="p_name")
    p_id = st.text_input("病歷號/身分證號", key="p_id", placeholder="例如: 00123")
    col1, col2 = st.columns(2)
    with col1:
        p_date = st.date_input("評估日期", value=date.today())
    with col2:
        # ✅ 新增：手動調整時間功能，預設為現在
        p_time = st.time_input("評估時間 (可用於補紀錄)", value=datetime.now().time())
    p_assessor = st.text_input("評估人", key="p_assessor")
    p_note = st.text_area("整體臨床總結備註 (此處會與動作備註合併)", height=100)

with tab2:
    st.info("動作備註將自動串接至總備註欄")
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
    
    matches = []
    for rule in TREATMENT_DATABASE:
        if rule["pair"].issubset(set(da_list)): matches.append(rule)
    if not matches:
        for rule in TREATMENT_DATABASE:
            if rule["pair"].issubset(set(ds_list)): matches.append(rule)

    if matches:
        for m in matches:
            is_deep = m["pair"] in DEEP_PAIRS
            if is_deep:
                # ✅ 修正深層判定的顯示顏色 (使用橘紅色區塊)
                st.markdown(f"""
                    <div class="deep-box">
                        <strong>💎 深層判定</strong><br>
                        動作組合: {' + '.join(m['pair'])}<br><br>
                        結果: {m['result']}
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("<div class='superficial-header'>🌿 淺層判定</div>", unsafe_allow_html=True)
                st.success(f"**{' + '.join(m['pair'])}** \n\n {m['result']}")
            
            imgs = [v for k, v in IMAGE_MAPPING.items() if k in m['result']]
            if imgs:
                with st.expander("🔍 檢視對應筋膜圖 (縮小 50%)"):
                    for img in imgs:
                        l, mid, r = st.columns([1, 2, 1])
                        try: mid.image(f"images/{img}", caption=f"對應: {img}", use_container_width=True)
                        except: mid.error(f"找不到檔案: images/{img}")
    else:
        st.info("目前組合尚未定義對應筋膜線。")

    st.divider()
    if st.button("🚀 完成評估並同步雲端"):
        if not p_name or not p_id:
            st.error("請輸入姓名與病歷號！")
        else:
            try:
                # 1. 合併備註邏輯
                final_combined_note = p_note if p_note else ""
                action_detail_list = [f"{act}:{user_action_notes[act].strip()}" for act in ACTIONS if user_action_notes[act].strip()]
                if action_detail_list:
                    combined_actions = "/".join(action_detail_list)
                    final_combined_note = f"{final_combined_note} | 詳細細節: {combined_actions}" if final_combined_note else combined_actions

                # ✅ 2. 修正時間抓取邏輯：抓取介面上的 p_date 與 p_time
                final_datetime_str = f"{p_date} {p_time.strftime('%H:%M')}"

                # 3. 建立紀錄
                record = {
                    "日期": final_datetime_str, 
                    "評估人": p_assessor, 
                    "病人姓名": p_name, 
                    "病歷號": f"'{p_id}",
                    "DA": ", ".join(da_list), 
                    "DS": ", ".join(ds_list),
                    "判定結果": " / ".join([m['result'] for m in matches]), 
                    "備註": final_combined_note
                }
                record.update(user_scores)
                
                df_new = pd.DataFrame([record])
                df_old = fetch_data_no_cache(conn)
                df_final = pd.concat([df_old, df_new], ignore_index=True)
                conn.update(worksheet="Sheet1", data=df_final)
                
                st.success(f"✅ 資料已同步！紀錄時間：{final_datetime_str}")
                st.balloons()
            except Exception as e:
                st.error(f"上傳失敗：{e}")

with tab4:
    st.subheader("📚 完整筋膜解剖圖譜")
    atlas = {
        "FF 功能線 (前+後)": ["FF1.jpg", "FF2.jpg"],
        "SBL 淺背線": ["SBL.jpg"],
        "SFL 淺前線": ["SFL.jpg"],
        "LL 側線": ["LL.jpg"],
        "SPL 螺旋線": ["SPL.jpg"], # ✅ 已統一格式
        "DFL 深前線": ["DFL.jpg"],
        "SFAL 淺前臂線": ["SFAL.jpg"],
        "SBAL 淺後臂線": ["SBAL.jpg"],
        "DFAL 深前臂線": ["DFAL.jpg"],
        "DBAL 深後臂線": ["DBAL.jpg"]
    }
    for title, imgs in atlas.items():
        with st.expander(f"📍 {title}"):
            for img in imgs:
                try: st.image(f"images/{img}", use_container_width=True)
                except: st.error(f"圖片遺失: images/{img}")

with tab5:
    st.subheader("📈 歷史恢復趨勢分析")
    search_id = st.text_input("輸入病歷號查詢歷史紀錄", key="q_id")
    
    if search_id:
        all_df = fetch_data_no_cache(conn)
        if not all_df.empty:
            all_df.columns = [str(c).strip() for c in all_df.columns]
            if "病歷號" in all_df.columns:
                all_df['病歷號'] = all_df['病歷號'].astype(str).str.lstrip("'").str.strip()
                target_id = str(search_id).strip()
                p_history = all_df[all_df["病歷號"] == target_id].sort_values("日期")
                
                if not p_history.empty:
                    st.success(f"找到 {len(p_history)} 筆歷史紀錄")
                    recent = p_history.tail(4)
                    
                    # 堆疊統計圖
                    stats_list = []
                    for _, row in recent.iterrows():
                        counts = {"DA": 0, "DS": 0, "FS": 0, "FA": 0}
                        for a in ACTIONS:
                            val = str(row.get(a, "")).strip()
                            if val in counts: counts[val] += 1
                        for lvl, cnt in counts.items():
                            stats_list.append({"日期": row["日期"], "等級": lvl, "次數": cnt})
                    
                    fig_bar = px.bar(pd.DataFrame(stats_list), x="日期", y="次數", color="等級", color_discrete_map=COLOR_MAP, category_orders={"等級": ["DA", "DS", "FS", "FA"]}, text_auto=True, height=400)
                    fig_bar.update_layout(xaxis_type='category', yaxis_title="動作次數")
                    st.plotly_chart(fig_bar, use_container_width=True)

                    st.divider()

                    # 雷達圖
                    fig_radar = go.Figure()
                    for _, row in recent.iterrows():
                        r_vals = [SCORE_MAP.get(str(row.get(a, "FA")).strip(), 4) for a in ACTIONS]
                        r_vals.append(r_vals[0]) 
                        fig_radar.add_trace(go.Scatterpolar(r=r_vals, theta=ACTIONS + [ACTIONS[0]], fill='toself', name=str(row['日期'])))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 4], tickvals=[1,2,3,4], ticktext=['DA','DS','FS','FA'])), margin=dict(t=30, b=30))
                    st.plotly_chart(fig_radar, use_container_width=True)

                    st.dataframe(p_history[["日期", "判定結果", "備註"]].sort_values("日期", ascending=False))
                else:
                    st.warning(f"查無資料：{target_id}")
