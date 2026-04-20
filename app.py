# ==========================================
# APP NAME: KPM 關鍵點評估系統
# VERSION: 1.1 (臨床決策加權版)
# BASE: V1.01 穩定地基
# UPDATE: 2026-04-08
# FEATURES: 
#   - CR 動作調整至第 5 位
#   - 新增 VAS 病人自覺分數滑桿 (0-10)
#   - 新增 ⭐ 關鍵點加權功能 (一鍵置頂重點)
#   - 自動修正時區 (UTC+8) 與 歷史圖表 (補) 字樣顯示
#   - 流量 429 報錯隱藏與中文友善提示
# ==========================================

import streamlit as st
from datetime import date, datetime, timedelta, timezone
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import google.generativeai as genai

# 初始化 Gemini API
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("API 金鑰未設定或設定錯誤，請檢查 secrets.toml")


# 測試區塊：檢查 API 是否運作
if st.sidebar.button("測試 AI 連線"):
    try:
        response = model.generate_content("請回覆：連線成功")
        st.sidebar.success(response.text)
    except Exception as e:
        st.sidebar.error(f"連線失敗: {e}")

# 1. 基礎設定與時區
st.set_page_config(page_title="KPM 筋膜評估系統 V1.1", layout="centered")
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

# CSS 樣式：包含加權置頂的視覺效果
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
        margin-bottom: 10px;
    }
    /* 加權重點處理樣式 */
    .priority-box {
        background-color: #F3E5F5;
        border: 2px solid #7B1FA2;
        padding: 15px;
        border-radius: 8px;
        color: #4A148C;
        margin-bottom: 15px;
        font-weight: bold;
    }
    hr { margin-top: 1rem; margin-bottom: 1rem; border-bottom: 2px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

st.title("🩺 KPM 關鍵點評估系統 V1.1")

# --- 2. 核心資料定義 ---
# CR 調整至第 5 位
ACTIONS = ["CF", "CE", "CRR", "CRL", "CR", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS"]
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
    
    # 新增 VAS 分數滑桿
    vas_score = st.slider("🤒 病人自覺整體分數 (10分最痛 / 0分不痛)", 0, 10, 5)
    
    p_assessor = st.text_input("評估人", key="p_assessor")
    p_note = st.text_area("整體臨床總結備註", height=100)

with tab2:
    st.info("請標註評估等級。若該動作為核心受限，請點選 ⭐ 加權。")
    user_scores = {}
    user_action_notes = {}
    user_priorities = {}
    
    for i, act in enumerate(ACTIONS, 1):
        st.markdown(f"<div class='action-title'>{i}. 動作: {act}</div>", unsafe_allow_html=True)
        col_eval, col_prio = st.columns([3, 1])
        with col_eval:
            user_scores[act] = st.segmented_control(label=act, options=["FA", "FS", "DS", "DA"], key=f"s_{act}", selection_mode="single", label_visibility="collapsed")
        with col_prio:
            user_priorities[act] = st.checkbox("⭐ 加權", key=f"prio_{act}")
        
        user_action_notes[act] = st.text_input(f"備註 ({act})", key=f"note_{act}")
        st.divider()

with tab3:
    st.subheader("📊 判定結果摘要")
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    priority_list = [k for k, v in user_priorities.items() if v]

    # 1. 頂端摘要
    if da_list or ds_list:
        st.write(f"🛑 **DA 項目:** {', '.join(da_list) if da_list else '無'}")
        st.write(f"⚠️ **DS 項目:** {', '.join(ds_list) if ds_list else '無'}")
        if priority_list:
            st.write(f"🌟 **關鍵加權點:** {', '.join(priority_list)}")
        st.divider()

    # 2. 判定邏輯
    matched_results = []
    source_list = da_list if da_list else ds_list
    
    for rule in TREATMENT_DATABASE:
        if rule["pair"].issubset(set(source_list)):
            # 檢查組合內是否有動作被加權
            is_prio = not rule["pair"].isdisjoint(set(priority_list))
            matched_results.append({"rule": rule, "is_prio": is_prio})

    # 3. 排序：加權項目置頂
    matched_results = sorted(matched_results, key=lambda x: x["is_prio"], reverse=True)

    if matched_results:
        for item in matched_results:
            m = item["rule"]
            is_prio = item["is_prio"]
            is_deep = m["pair"] in DEEP_PAIRS
            
            # 加權視覺處理
            if is_prio:
                st.markdown(f"""
                    <div class="priority-box">
                        🔥 重點處理項目<br>
                        動作組合: {' + '.join(sorted(list(m['pair'])))}<br><br>
                        結果: {m['result']}
                    </div>
                """, unsafe_allow_html=True)
            elif is_deep:
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
            
            # 圖片顯示
            imgs = [v for k, v in IMAGE_MAPPING.items() if k in m['result']]
            if imgs:
                with st.expander("🔍 檢視圖譜 (50%)"):
                    for img in imgs:
                        l, mid, r = st.columns([1, 2, 1])
                        try: mid.image(f"images/{img}", use_container_width=True)
                        except: mid.error(f"找不到圖片: {img}")
    else:
        st.info("目前點選組合尚未觸發判定。")

    st.divider()
    if st.button("🚀 完成評估並同步雲端"):
        if not p_name or not p_id:
            st.error("請輸入姓名與病歷號！")
        else:
            try:
                # 備註合併邏輯
                act_notes = [f"{a}:{user_action_notes[a].strip()}" for a in ACTIONS if user_action_notes[a].strip()]
                # 若有加權，也在細節中標註
                prio_tags = [f"{a}(⭐)" for a in priority_list]
                combined_details = "/".join(act_notes + prio_tags)
                final_note = f"{p_note} | 詳細: {combined_details}" if p_note and combined_details else (p_note or combined_details)

                # 時間邏輯
                now_tw = datetime.now(tz_taiwan)
                final_dt_str = now_tw.strftime("%Y-%m-%d %H:%M") if p_date >= now_tw.date() else f"{p_date} (補)"

                # 同步資料
                record = {
                    "日期": final_dt_str, "評估人": p_assessor, "病人姓名": p_name, "病歷號": f"'{p_id}",
                    "病人自覺分數": vas_score, "加權關鍵點": ", ".join(priority_list),
                    "判定結果": " / ".join([res['rule']['result'] for res in matched_results]), 
                    "備註": final_note
                }
                record.update(user_scores)
                
                df_old = fetch_data_no_cache(conn)
                df_final = pd.concat([df_old, pd.DataFrame([record])], ignore_index=True)
                conn.update(worksheet="Sheet1", data=df_final)
                st.success(f"✅ 資料已同步！時間：{final_dt_str}"); st.balloons()
            except Exception as e:
                if "429" in str(e):
                    st.error("⚠️ 雲端連線過於繁忙，請等待約 60 秒後再試一次。")
                else:
                    st.error(f"同步失敗: {e}")

with tab4:
    st.subheader("📚 完整筋膜解剖圖譜")
    atlas = {"FF 功能線 (前+後)": ["FF1.jpg", "FF2.jpg"], "SBL 淺背線": ["SBL.jpg"], "SFL 淺前線": ["SFL.jpg"], "LL 側線": ["LL.jpg"], "SPL 螺旋線": ["SPL.jpg"], "DFL 深前線": ["DFL.jpg"], "SFAL 淺前臂線": ["SFAL.jpg"], "SBAL 淺後臂線": ["SBAL.jpg"], "DFAL 深前臂線": ["DFAL.jpg"], "DBAL 深後臂線": ["DBAL.jpg"]}
    for title, imgs in atlas.items():
        with st.expander(f"📍 {title}"):
            for img in imgs: st.image(f"images/{img}", use_container_width=True)

with tab5:
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
                    # 排序修正
                    p_history['sort_dt'] = pd.to_datetime(p_history['日期'].str.replace(" (補)", "", regex=False), errors='coerce')
                    p_history = p_history.sort_values("sort_dt")
                    
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
                    
                    fig_bar = px.bar(pd.DataFrame(stats_list), x="日期", y="次數", color="等級", color_discrete_map=COLOR_MAP, category_orders={"等級": ["DA", "DS", "FS", "FA"]}, text_auto=True)
                    fig_bar.update_layout(xaxis_type='category') # 核心：確保 (補) 出現
                    st.plotly_chart(fig_bar, use_container_width=True)

                    # 雷達圖
                    fig_radar = go.Figure()
                    for _, row in recent.iterrows():
                        r_vals = [SCORE_MAP.get(str(row.get(a, "FA")).strip(), 4) for a in ACTIONS]; r_vals.append(r_vals[0])
                        fig_radar.add_trace(go.Scatterpolar(r=r_vals, theta=ACTIONS + [ACTIONS[0]], fill='toself', name=str(row['日期'])))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 4], tickvals=[1,2,3,4], ticktext=['DA','DS','FS','FA'])))
                    st.plotly_chart(fig_radar, use_container_width=True)

                    st.dataframe(p_history.sort_values("sort_dt", ascending=False)[["日期", "判定結果", "備註"]])
