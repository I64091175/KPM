import streamlit as st
from datetime import date
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go

# 1. 基礎網頁設定與快取設置
st.set_page_config(page_title="KPM 筋膜評估系統", layout="centered")

# 離線快取函數：圖片讀取優化
@st.cache_data
def get_image(path):
    return path

# 離線快取函數：Sheets 讀取優化 (每 10 分鐘更新一次或手動清除)
@st.cache_data(ttl=600)
def fetch_data(_conn):
    return _conn.read(worksheet="Sheet1", ttl=0)

# 2. 連接資料庫
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

# --- 3. 資料庫與參數設定 ---
ACTIONS = ["CF", "CE", "CRR", "CRL", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS", "CR"]
SCORE_MAP = {"FA": 4, "FS": 3, "DS": 2, "DA": 1} # 雷達圖分數化

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

DEEP_PAIRS = [{"CE", "MSE"}, {"MSRR", "MSSBL"}, {"MSRL", "MSSBR"}, {"CE", "LAU"}, {"CE", "RAU"}, {"CRR", "LAD"}, {"CRL", "RAD"}]
IMAGE_MAPPING = {
    "螺旋線": "SPL.jpg", "後功能線": "FF1.jpg", "前功能線": "FF2.jpg",
    "淺背線": "SBL.jpg", "淺前線": "SFL.jpg", "側線": "LL.jpg",
    "深前線": "DFL.jpg", "深前臂線": "DFAL.jpg", "深後臂線": "DBAL.jpg",
    "淺前臂線": "SFAL.jpg", "淺後臂線": "SBAL.jpg"
}

# --- 4. 分頁介面 ---
tabs = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜", "📈 歷史追蹤"])

# [分頁1-4 邏輯簡化整合]
with tabs[0]:
    p_name = st.text_input("病人姓名")
    p_id = st.text_input("病歷號/身分證號")
    p_date = st.date_input("評估日期", value=date.today())
    p_assessor = st.text_input("評估人")
    p_note = st.text_area("備註")

with tabs[1]:
    user_scores = {}
    for act in ACTIONS:
        user_scores[act] = st.segmented_control(act, options=["FA", "FS", "DS", "DA"], key=f"btn_{act}")

with tabs[2]:
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    matches = [r for r in TREATMENT_DATABASE if r["pair"].issubset(set(da_list))] or \
              [r for r in TREATMENT_DATABASE if r["pair"].issubset(set(ds_list))]

    if matches:
        for m in matches:
            style = st.warning if m["pair"] in DEEP_PAIRS else st.success
            style(f"**{' + '.join(m['pair'])}**\n\n{m['result']}")
            img_files = [img for k, img in IMAGE_MAPPING.items() if k in m['result']]
            if img_files:
                with st.expander("🔍 檢視對應筋膜圖"):
                    for f in img_files:
                        l, mid, r = st.columns([1, 2, 1])
                        mid.image(get_image(f"images/{f}"), use_container_width=True)
    
    if st.button("🚀 上傳結果"):
        # 存檔時將每個動作的分數也存入，以便未來繪製雷達圖
        data_to_save = {
            "日期": str(p_date), "病人姓名": p_name, "病歷號": p_id, "評估人": p_assessor,
            "判定結果": " / ".join([m['result'] for m in matches]), "備註": p_note
        }
        data_to_save.update(user_scores) # 將各動作分數存入 Excel 欄位
        df_new = pd.DataFrame([data_to_save])
        df_old = fetch_data(conn)
        updated_df = pd.concat([df_old, df_new], ignore_index=True)
        conn.update(worksheet="Sheet1", data=updated_df)
        st.cache_data.clear() # 清除快取以刷新歷史紀錄
        st.balloons()

with tabs[3]:
    atlas = {"FF 功能線": ["FF1.jpg", "FF2.jpg"], "SBL 淺背線": ["SBL.jpg"], "SFL 淺前線": ["SFL.jpg"], "LL 側線": ["LL.jpg"], "SPL 螺旋線": ["SPL.jpg"], "DFL 深前線": ["DFL.jpg"], "SFAL 淺前臂線": ["SFAL.jpg"], "SBAL 淺後臂線": ["SBAL.jpg"], "DFAL 深前臂線": ["DFAL.jpg"], "DBAL 深後臂線": ["DBAL.jpg"]}
    for title, imgs in atlas.items():
        with st.expander(f"📍 {title}"):
            for img in imgs: st.image(get_image(f"images/{img}"), use_container_width=True)

# --- 5. 第五頁：歷史追蹤與雷達圖 ---
with tabs[4]:
    st.subheader("📊 歷史功能進步曲線")
    search_id = st.text_input("輸入病歷號以查詢歷史紀錄", key="search_history")
    
    if search_id:
        history_df = fetch_data(conn)
        # 過濾該病人的資料
        patient_records = history_df[history_df["病歷號"] == search_id].sort_values(by="日期")
        
        if not patient_records.empty:
            st.write(f"找到 {len(patient_records)} 次紀錄。正在顯示最近 4 次對比：")
            
            # 取得最近 4 次紀錄
            recent_records = patient_records.tail(4)
            
            # 建立雷達圖
            fig = go.Figure()
            
            for i, (_, row) in enumerate(recent_records.iterrows()):
                # 將動作名稱與對應分數提取出來
                r_values = []
                for act in ACTIONS:
                    val = row.get(act, "FA") # 若無紀錄則預設 FA
                    r_values.append(SCORE_MAP.get(val, 4))
                
                # Plotly 雷達圖需要頭尾相連
                r_values.append(r_values[0])
                theta = ACTIONS + [ACTIONS[0]]
                
                fig.add_trace(go.Scatterpolar(
                    r=r_values,
                    theta=theta,
                    fill='toself',
                    name=f"{row['日期']}",
                    opacity=0.6 if i < len(recent_records)-1 else 0.8
                ))

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 4], tickvals=[1, 2, 3, 4], ticktext=['DA', 'DS', 'FS', 'FA'])
                ),
                showlegend=True,
                title=f"{search_id} 功能恢復雷達圖"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 顯示表格清單
            st.write("📋 歷史判定詳情：")
            st.dataframe(patient_records[["日期", "判定結果", "備註"]].sort_values(by="日期", ascending=False))
        else:
            st.info("尚未找到該病歷號的歷史資料。")
