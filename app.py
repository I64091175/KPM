import streamlit as st
from datetime import date
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基礎網頁設定
st.set_page_config(page_title="KPM 筋膜評估系統", layout="centered")

# 2. 建立 Google Sheets 連接
conn = st.connection("gsheets", type=GSheetsConnection)

# CSS 優化
st.markdown("""
    <style>
    .stHeader { font-size: 1.2rem !important; color: #2c3e50; }
    .action-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 5px; color: #1E88E5; }
    .superficial-header { color: #2E7D32; font-weight: bold; border-left: 5px solid #2E7D32; padding-left: 10px; margin-top: 20px; }
    .deep-header { color: #E65100; font-weight: bold; border-left: 5px solid #E65100; padding-left: 10px; margin-top: 20px; }
    hr { margin-top: 1rem; margin-bottom: 1rem; border-bottom: 2px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

st.title("🩺 KPM 關鍵點評估系統")

# --- 3. 完整邏輯資料庫 ---
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

# 第三頁圖片自動匹配清單
IMAGE_MAPPING = {
    "螺旋線": "SPL.jpg", "後功能線": "FF1.jpg", "前功能線": "FF2.jpg",
    "淺背線": "SBL.jpg", "淺前線": "SFL.jpg", "側線": "LL.jpg",
    "深前線": "DFL.jpg", "深前臂線": "DFAL.jpg", "深後臂線": "DBAL.jpg",
    "淺前臂線": "SFAL.jpg", "淺後臂線": "SBAL.jpg"
}

# --- 4. 介面設計 ---
tab1, tab2, tab3, tab4 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜"])

with tab1:
    st.subheader("基本資料紀錄")
    p_name = st.text_input("病人姓名", placeholder="請輸入姓名")
    p_id = st.text_input("病歷號/身分證號", placeholder="請輸入識別碼")
    col1, col2 = st.columns(2)
    with col1: p_date = st.date_input("評估日期", value=date.today())
    with col2: p_assessor = st.text_input("評估人", placeholder="治療師姓名")
    p_note = st.text_area("整體臨床總結備註", height=100)

with tab2:
    st.info("直接點選等級按鈕")
    actions = ["CF", "CE", "CRR", "CRL", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS", "CR"]
    user_scores = {}
    for i, act in enumerate(actions, 1):
        with st.container():
            st.markdown(f"<div class='action-title'>{i}. 動作: {act}</div>", unsafe_allow_html=True)
            user_scores[act] = st.segmented_control(label=f"s_{act}", options=["FA", "FS", "DA", "DS"], key=f"btn_{act}", selection_mode="single", label_visibility="collapsed")
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

    # 第三頁圖片縮小 50% 顯示函式
    def display_matched_images_small(result_text):
        images_to_show = [img for key, img in IMAGE_MAPPING.items() if key in result_text]
        if images_to_show:
            for img_file in images_to_show:
                l, mid, r = st.columns([1, 2, 1]) # 使用 1:2:1 比例達成 50% 寬度置中
                try: mid.image(f"images/{img_file}", caption=f"對應: {img_file}", use_container_width=True)
                except: mid.error(f"找不到檔案: images/{img_file}")

    if matches:
        superficial_res, deep_res = [], []
        for m in matches:
            if m["pair"] in DEEP_PAIRS: deep_res.append(m)
            else: superficial_res.append(m)

        if superficial_res:
            st.markdown("<div class='superficial-header'>🌿 淺層判定</div>", unsafe_allow_html=True)
            for m in superficial_res:
                st.success(f"**{' + '.join(sorted(list(m['pair'])))}** \n\n {m['result']}")
                display_matched_images_small(m['result'])

        if deep_res:
            st.markdown("<div class='deep-header'>💎 深層判定</div>", unsafe_allow_html=True)
            for m in deep_res:
                st.warning(f"**{' + '.join(sorted(list(m['pair'])))}** \n\n {m['result']}")
                display_matched_images_small(m['result'])
    else: st.info("目前組合尚未定義對應筋膜線。")

    st.divider()
    if st.button("🚀 完成評估並上傳雲端"):
        if not p_name: st.error("請先輸入姓名")
        else:
            try:
                new_row = pd.DataFrame([{"日期": str(p_date), "評估人": p_assessor, "病人姓名": p_name, "病歷號": p_id, "DA": ", ".join(da_list), "DS": ", ".join(ds_list), "判定結果": " / ".join([m['result'] for m in matches]), "備註": p_note}])
                existing_data = conn.read(worksheet="Sheet1", ttl=0)
                updated_df = pd.concat([existing_data, new_row], ignore_index=True) if existing_data is not None else new_row
                conn.update(worksheet="Sheet1", data=updated_df)
                st.balloons(); st.success("✅ 資料已同步至 Google Sheets")
            except Exception as e: st.error(f"❌ 上傳失敗: {e}")

# --- 第四頁：📚 筋膜圖譜 ---
with tab4:
    st.subheader("🔍 完整筋膜解剖手冊")
    
    # 這裡修正了標題與新增了淺層臂線
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
    
    for title, imgs in atlas.items():
        with st.expander(f"📍 {title}"):
            for img_path in imgs:
                try: st.image(f"images/{img_path}", use_container_width=True)
                except: st.error(f"圖片遺失: images/{img_path} (請確認檔案已上傳至 GitHub)")
