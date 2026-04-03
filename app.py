import streamlit as st
from datetime import date, datetime, timedelta, timezone
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px

# 1. 基礎設定與台灣時區 (UTC+8)
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

# CSS 樣式：美化深淺層判定與動作標題
st.markdown("""
    <style>
    .stHeader { font-size: 1.2rem !important; color: #2c3e50; }
    .action-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 5px; color: #1E88E5; }
    .superficial-header { color: #2E7D32; font-weight: bold; border-left: 5px solid #2E7D32; padding-left: 10px; margin-top: 20px; }
    /* 深層判定專用樣式 */
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

# --- 2. 核心資料定義 ---
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

# --- 3. 介面分頁 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜", "📈 歷史追蹤"])

with tab1:
    st.subheader("👤 病人基本資料")
    p_name = st.text_input("病人姓名", key="p_name")
    p_id = st.text_input("病歷號/身分證號", key="p_id", placeholder="例如: 00123")
    today_taiwan = datetime.now(tz_taiwan).date()
    p_date = st.date_input("評估日期", value=today_taiwan)
    p_assessor = st.text_input("評估人", key="p_assessor")
    p_note = st.text_area("整體臨床總結備註", height=100)

with tab2:
    st.info("動作備註將自動串接至最後的備註欄")
    user_scores = {}
    user_action_notes = {}
    for i, act in enumerate(ACTIONS, 1):
        st.markdown(f"<div class='action-title'>{i}. 動作: {act}</div>", unsafe_allow_html=True)
        user_scores[act] = st.segmented_control(label=act, options=["FA", "FS", "DS", "DA"], key=f"s_{act}", selection_mode="single", label_visibility="collapsed")
        user_action_notes[act] = st.text_input(f"備註 ({act})", key=f"note_{act}", placeholder="在此輸入特定痛點...")
        st.divider()

with tab3:
    st.subheader("📊 判定結果摘要")
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    
    matches = []
    # 優先匹配 DA 組
    for rule in TREATMENT_DATABASE:
        if rule["pair"].issubset(set(da_list)): matches.append(rule)
    # 若無 DA 則匹配 DS 組
    if not matches:
        for rule in TREATMENT_DATABASE:
            if rule["pair"].issubset(set(ds_list)): matches.append(rule)

    if matches:
        for m in matches:
            is_deep = m["pair"] in DEEP_PAIRS
            if is_deep:
                st.markdown(f"""
                    <div class="deep-box">
                        <strong>💎 深層判定</strong><br>
                        動作組合: {' + '.join(sorted(list(m['pair'])))}<br><br>
                        結果: {m['result']}
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("<div class='superficial-header'>🌿 淺層判定</div>", unsafe_allow_html=True)
                st.success(f"**{' + '.join(sorted(list(m['pair'])))}** \n\n {m['result']}")
            
            # 圖片顯示邏輯：50% 寬度、置中、摺疊面板
            imgs = [v for k, v in IMAGE_MAPPING.items() if k in m['result']]
            if imgs:
                with st.expander("🔍 檢視對應筋膜圖 (縮小 50%)"):
                    for img_file in imgs:
                        l, mid, r = st.columns([1, 2, 1])
                        try: mid.image(f"images/{img_file}", caption=f"對應: {img_file}", use_container_width=True)
                        except: mid.error(f"找不到圖片: images/{img_file}")
    else:
        st.info("目前組合尚未定義對應筋膜線。")

    st.divider()
    if st.button("🚀 完成評估並同步雲端"):
        if not p_name or not p_id:
            st.error("請輸入姓名與病歷號！")
        else:
            try:
                # 1. 備註合併邏輯 (動作:內容/動作:內容)
                action_detail_list = [f"{act}:{user_action_notes[act].strip()}" for act in ACTIONS if user_action_notes[act].strip()]
                combined_details = "/".join(action_detail_list)
                final_combined_note = p_note if p_note else ""
                if combined_details:
                    final_combined_note = f"{final_combined_note} | 詳細細節: {combined_details}" if final_combined_note else combined_details

                # 2. 自動時間邏輯 (今天顯示時間，過去顯示補)
                now_taiwan = datetime.now(tz_taiwan)
                if p_date >= now_taiwan.date():
                    final_datetime_str = now_taiwan.strftime("%Y-%m-%d %H:%M")
                else:
                    final_datetime_str = f"{p_date} (補)"

                # 3. 建立並同步紀錄
                record = {
                    "日期": final_datetime_str, "評估人": p_assessor, "病人姓名": p_name, "病歷號": f"'{p_id}",
                    "DA": ", ".join(da_list), "DS": ", ".join(ds_list),
                    "判定結果": " / ".join([m['result'] for m in matches]), "備註": final_combined_note
                }
                record.update(user_scores) # 存入評估等級以便繪圖
                
                df_old = fetch_data_no_cache(conn)
                df_final = pd.concat([df_old, pd.DataFrame([record])], ignore_index=True)
                conn.update(worksheet="Sheet1", data=df_final)
                
                st.success(f"✅ 資料已同步！紀錄時間：{final_datetime_str}")
                st.balloons()
            except Exception as e:
                st.error(f"上傳失敗：{e}")

with tab4:
    st.subheader("📚 完整筋膜解剖圖譜")
    # 標題與分組：英在前、中在後
    atlas = {
        "FF 功能線 (前+後)": ["FF1.jpg", "FF2.jpg"],
        "SBL 淺背線": ["SBL.jpg"],
        "SFL 淺前線": ["SFL.jpg"],
        "LL 側線": ["LL.jpg"],
        "SPL 螺旋線": ["SPL.jpg"],
        "DFL 深前線": ["DFL.jpg"],
        "SFAL 淺前臂線": ["SFAL.jpg"],
        "SBAL 淺後臂線": ["SBAL.jpg"],
        "DFAL 深前臂線": ["DFAL.jpg"],
        "DBAL 深後臂線": ["DBAL.jpg"]
    }
    for title, img_list in atlas.items():
        with st.expander(f"📍 {title}"):
            for img_name in img_list:
                try: st.image(f"images/{img_name}", use_container_width=True)
                except: st.error(f"找不到圖片: {img_name}")

with tab5:
    st.subheader("📈 歷史恢復趨勢分析")
    search_id = st.text_input("輸入病歷號查詢歷史紀錄", key="q_id")
    
    if search_id:
        all_df = fetch_data_no_cache(conn)
        if not all_df.empty:
            # 欄位防呆與病歷號清理
            all_df.columns = [str(c).strip() for c in all_df.columns]
            if "病歷號" in all_df.columns:
                all_df['病歷號'] = all_df['病歷號'].astype(str).str.lstrip("'").str.strip()
                target_id = str(search_id).strip()
                p_history = all_df[all_df["病歷號"] == target_id].copy()
                
                if not p_history.empty:
                    # 排序邏輯：解析日期物件進行精確排序
                    p_history['sort_date'] = pd.to_datetime(p_history['日期'].str.replace(" (補)", "", regex=False), errors='coerce')
                    p_history = p_history.sort_values("sort_date")
                    
                    st.success(f"找到 {len(p_history)} 筆紀錄，顯示最近 4 次：")
                    recent = p_history.tail(4)
                    
                    # 1. 堆疊柱狀圖：顯示 DA/DS/FS/FA 的出現次數
                    stats_list = []
                    for _, row in recent.iterrows():
                        counts = {"DA": 0, "DS": 0, "FS": 0, "FA": 0}
                        for a in ACTIONS:
                            val = str(row.get(a, "")).strip()
                            if val in counts: counts[val] += 1
                        for lvl, cnt in counts.items():
                            stats_list.append({"日期": row["日期"], "等級": lvl, "次數": cnt})
                    
                    fig_bar = px.bar(pd.DataFrame(stats_list), x="日期", y="次數", color="等級", 
                                     color_discrete_map=COLOR_MAP, 
                                     category_orders={"等級": ["DA", "DS", "FS", "FA"]}, 
                                     text_auto=True, height=400)
                    fig_bar.update_layout(xaxis_type='category', yaxis_title="動作次數 (共16項)")
                    st.plotly_chart(fig_bar, use_container_width=True)

                    st.divider()

                    # 2. 雷達圖：顯示各動作功能方位
                    fig_radar = go.Figure()
                    for _, row in recent.iterrows():
                        r_vals = [SCORE_MAP.get(str(row.get(a, "FA")).strip(), 4) for a in ACTIONS]
                        r_vals.append(r_vals[0]) 
                        fig_radar.add_trace(go.Scatterpolar(r=r_vals, theta=ACTIONS + [ACTIONS[0]], 
                                                           fill='toself', name=str(row['日期'])))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 4], 
                                                                      tickvals=[1,2,3,4], 
                                                                      ticktext=['DA','DS','FS','FA'])), 
                                            margin=dict(t=30, b=30))
                    st.plotly_chart(fig_radar, use_container_width=True)

                    # 3. 歷史列表
                    st.write("📋 詳細歷史列表：")
                    st.dataframe(p_history[["日期", "判定結果", "備註"]].sort_values("sort_date", ascending=False))
                else:
                    st.warning(f"查無資料：{target_id}")
