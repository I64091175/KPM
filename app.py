import streamlit as st
from datetime import date
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px # 新增 px 用於統計圖

# 1. 基礎設定
st.set_page_config(page_title="KPM 筋膜評估系統", layout="centered")

def fetch_data_no_cache(_conn):
    try:
        return _conn.read(worksheet="Sheet1", ttl=0)
    except Exception as e:
        st.error(f"讀取資料庫失敗: {e}")
        return pd.DataFrame()

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. 核心參數 ---
ACTIONS = ["CF", "CE", "CRR", "CRL", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS", "CR"]
SCORE_MAP = {"DA": 1, "DS": 2, "FS": 3, "FA": 4}
COLOR_MAP = {"DA": "#EF553B", "DS": "#FFA15A", "FS": "#636EFA", "FA": "#00CC96"} # 紅白橘綠專業配色

# [前四頁邏輯維持不變，僅節錄核心修改處]
# ... (略過 Tab 1-4 的 UI 代碼以節省空間，請沿用之前的內容) ...

# --- 3. 第五頁：歷史追蹤 (新增統計功能) ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜", "📈 歷史追蹤"])

# (中間 Tab 1-4 代碼請保留...)

with tab5:
    st.subheader("📊 歷史功能恢復追蹤")
    search_id = st.text_input("輸入病歷號查詢歷史紀錄", key="q_id")
    
    if search_id:
        all_df = fetch_data_no_cache(conn)
        if not all_df.empty:
            all_df.columns = [str(c).strip() for c in all_df.columns]
            all_df['病歷號'] = all_df['病歷號'].astype(str).str.lstrip("'").str.strip()
            target_id = str(search_id).strip()
            
            p_history = all_df[all_df["病歷號"] == target_id].sort_values("日期")
            
            if not p_history.empty:
                st.success(f"找到 {len(p_history)} 筆紀錄")
                recent = p_history.tail(4)
                
                # --- 新增：等級出現次數統計 (堆疊圖數據處理) ---
                stats_list = []
                for _, row in recent.iterrows():
                    counts = {"DA": 0, "DS": 0, "FS": 0, "FA": 0}
                    for a in ACTIONS:
                        val = str(row.get(a, "")).strip()
                        if val in counts:
                            counts[val] += 1
                    
                    for level, count in counts.items():
                        stats_list.append({
                            "日期": row["日期"],
                            "等級": level,
                            "出現次數": count
                        })
                
                stats_df = pd.DataFrame(stats_list)

                # --- 繪製：堆疊柱狀圖 (看比例進步最直覺) ---
                st.write("🟢 **各等級分布進步趨勢** (理想情況：綠色條塊應隨時間增加)")
                fig_bar = px.bar(
                    stats_df, x="日期", y="出現次數", color="等級",
                    color_discrete_map=COLOR_MAP,
                    category_orders={"等級": ["DA", "DS", "FS", "FA"]},
                    text_auto=True, # 直接在條塊上顯示數字
                    title=f"病人 {target_id} 評估等級比例變化"
                )
                fig_bar.update_layout(xaxis_type='category')
                st.plotly_chart(fig_bar, use_container_width=True)

                st.divider()

                # --- 繪製：雷達圖 (看失能方位) ---
                st.write("🧭 **功能失能方位圖** (雷達圖：看哪一側動作受限)")
                fig_radar = go.Figure()
                for _, row in recent.iterrows():
                    r_vals = [SCORE_MAP.get(str(row.get(a, "FA")).strip(), 4) for a in ACTIONS]
                    r_vals.append(r_vals[0]) 
                    fig_radar.add_trace(go.Scatterpolar(
                        r=r_vals, theta=ACTIONS + [ACTIONS[0]],
                        fill='toself', name=str(row['日期'])
                    ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 4], tickvals=[1,2,3,4], ticktext=['DA','DS','FS','FA'])),
                )
                st.plotly_chart(fig_radar, use_container_width=True)

                # 顯示歷史列表
                st.dataframe(p_history[["日期", "判定結果", "備註"]].sort_values("日期", ascending=False))
            else:
                st.warning(f"查無此病歷號：{target_id}")
