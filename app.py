import streamlit as st
from datetime import date
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go

# 1. 基礎設定與快取優化 (離線快取邏輯)
st.set_page_config(page_title="KPM 筋膜評估系統", layout="centered")

@st.cache_data(ttl=600)
def fetch_data(_conn):
    try:
        return _conn.read(worksheet="Sheet1", ttl=0)
    except:
        return pd.DataFrame()

# 建立連線
conn = st.connection("gsheets", type=GSheetsConnection)

# CSS 樣式
st.markdown("""
    <style>
    .stHeader { font-size: 1.2rem !important; color: #2c3e50; }
    .superficial-header { color: #2E7D32; font-weight: bold; border-left: 5px solid #2E7D32; padding-left: 10px; margin-top: 20px; }
    .deep-header { color: #E65100; font-weight: bold; border-left: 5px solid #E65100; padding-left: 10px; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🩺 KPM 關鍵點評估系統")

# --- 2. 核心資料定義 ---
ACTIONS = ["CF", "CE", "CRR", "CRL", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS", "CR"]
# 分數對應：DA(1), DS(2), FS(3), FA(4)
SCORE_MAP = {"DA": 1, "DS": 2, "FS": 3, "FA": 4}

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
    st.subheader("基本資料紀錄")
    p_name = st.text_input("病人姓名", placeholder="姓名")
    p_id = st.text_input("病歷號/身分證號", placeholder="ID")
    col1, col2 = st.columns(2)
    with col1: p_date = st.date_input("評估日期", value=date.today())
    with col2: p_assessor = st.text_input("評估人", placeholder="治療師")
    p_note = st.text_area("整體臨床備註", height=100)

with tab2:
    st.info("請點選各項動作之評估等級")
    user_scores = {}
    for i, act in enumerate(ACTIONS, 1):
        st.markdown(f"**{i}. 動作: {act}**")
        user_scores[act] = st.segmented_control(label=act, options=["FA", "FS", "DS", "DA"], key=f"s_{act}", selection_mode="single", label_visibility="collapsed")
        st.divider()

with tab3:
    st.subheader("📊 判定結果與建議")
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
            style_class = "deep-header" if m["pair"] in DEEP_PAIRS else "superficial-header"
            label = "💎 深層判定" if m["pair"] in DEEP_PAIRS else "🌿 淺層判定"
            st.markdown(f"<div class='{style_class}'>{label}</div>", unsafe_allow_html=True)
            
            if m["pair"] in DEEP_PAIRS: st.warning(f"**{' + '.join(m['pair'])}** \n\n {m['result']}")
            else: st.success(f"**{' + '.join(m['pair'])}** \n\n {m['result']}")
            
            # 圖片展開邏輯
            imgs = [v for k, v in IMAGE_MAPPING.items() if k in m['result']]
            if imgs:
                with st.expander("🔍 檢視對應筋膜圖"):
                    for img in imgs:
                        l, mid, r = st.columns([1, 2, 1])
                        try: mid.image(f"images/{img}", use_container_width=True)
                        except: mid.error(f"找不到圖片: images/{img}")
    else:
        st.info("目前組合尚未定義對應筋膜線。")

    st.divider()
    if st.button("🚀 完成評估並同步雲端"):
        if not p_name or not p_id:
            st.error("請輸入病人姓名與病歷號！")
        else:
            try:
                # 建立新資料行，包含所有動作分數以便後續繪製雷達圖
                record = {
                    "日期": str(p_date), "評估人": p_assessor, "病人姓名": p_name, "病歷號": p_id,
                    "DA": ", ".join(da_list), "DS": ", ".join(ds_list),
                    "判定結果": " / ".join([m['result'] for m in matches]), "備註": p_note
                }
                record.update(user_scores) # 展開 16 個動作欄位
                
                df_new = pd.DataFrame([record])
                df_old = fetch_data(conn)
                df_final = pd.concat([df_old, df_new], ignore_index=True)
                
                conn.update(worksheet="Sheet1", data=df_final)
                st.cache_data.clear() # 清除快取，讓歷史頁面更新
                st.balloons()
                st.success("✅ 資料已同步！")
            except Exception as e:
                st.error(f"上傳失敗：{e}")

with tab4:
    st.subheader("📚 筋膜解剖圖譜")
    atlas = {
        "FF 功能線 (前+後)": ["FF1.jpg", "FF2.jpg"], "SBL 淺背線": ["SBL.jpg"],
        "SFL 淺前線": ["SFL.jpg"], "LL 側線": ["LL.jpg"], "SPL 螺旋線": ["SPL.jpg"],
        "DFL 深前線": ["DFL.jpg"], "SFAL 淺前臂線": ["SFAL.jpg"], "SBAL 淺後臂線": ["SBAL.jpg"],
        "DFAL 深前臂線": ["DFAL.jpg"], "DBAL 深後臂線": ["DBAL.jpg"]
    }
    for title, imgs in atlas.items():
        with st.expander(f"📍 {title}"):
            for img in imgs:
                try: st.image(f"images/{img}", use_container_width=True)
                except: st.error(f"找不到圖片: {img}")

with tab5:
    st.subheader("📈 歷史恢復追蹤")
    search_id = st.text_input("輸入病歷號查詢歷史雷達圖")
    if search_id:
        all_df = fetch_data(conn)
        if not all_df.empty and "病歷號" in all_df.columns:
            p_history = all_df[all_df["病歷號"] == search_id].sort_values("日期")
            if not p_history.empty:
                # 只取最近 4 次
                recent = p_history.tail(4)
                fig = go.Figure()
                for _, row in recent.iterrows():
                    # 提取動作分數並轉換為 1-4
                    r_vals = [SCORE_MAP.get(row.get(a, "FA"), 4) for a in ACTIONS]
                    r_vals.append(r_vals[0]) # 閉合雷達圖
                    fig.add_trace(go.Scatterpolar(
                        r=r_vals, theta=ACTIONS + [ACTIONS[0]],
                        fill='toself', name=row['日期']
                    ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 4], tickvals=[1,2,3,4], ticktext=['DA','DS','FS','FA'])),
                    title=f"病人 {search_id} 恢復趨勢"
                )
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(p_history[["日期", "判定結果", "備註"]].sort_values("日期", ascending=False))
            else:
                st.info("查無此病歷號紀錄。")
