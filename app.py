import streamlit as st
from datetime import date
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基礎網頁設定 (這行必須在最前面！)
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
    {"pair": {"CRL", "RAD"}, "right": "右深後臂線"}
]

DEEP_PAIRS = [{"CE", "MSE"}, {"MSRR", "MSSBL"}, {"MSRL", "MSSBR"}, {"CE", "LAU"}, {"CE", "RAU"}, {"CRR", "LAD"}, {"CRL", "RAD"}]

# --- 4. 介面設計 ---
tab1, tab2, tab3 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果"])

with tab1:
    st.subheader("基本資料紀錄")
    p_name = st.text_input("病人姓名", placeholder="請輸入姓名")
    p_id = st.text_input("病歷號/身分證號", placeholder="請輸入識別碼")
    col1, col2 = st.columns(2)
    with col1:
        p_date = st.date_input("評估日期", value=date.today())
    with col2:
        p_assessor = st.text_input("評估人", placeholder="治療師姓名")
    p_note = st.text_area("整體臨床總結備註", height=100)

with tab2:
    st.info("直接點選等級按鈕，並可在下方輸入備註")
    actions = ["CF", "CE", "CRR", "CRL", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS", "CR"]
    user_scores, user_remarks = {}, {}
    for i, act in enumerate(actions, 1):
        with st.container():
            st.markdown(f"<div class='action-title'>{i}. 動作: {act}</div>", unsafe_allow_html=True)
            score = st.segmented_control(label=f"s_{act}", options=["FA", "FS", "DA", "DS"], key=f"btn_{act}", selection_mode="single", default=None, label_visibility="collapsed")
            user_scores[act] = score
            user_remarks[act] = st.text_input(f"備註 ({act})", key=f"note_{act}", placeholder="特殊表現...")
            st.divider()

with tab3:
    st.subheader("📋 評分摘要")
    scores_categories = {"🔴 DA": [k for k, v in user_scores.items() if v == "DA"], "🟠 DS": [k for k, v in user_scores.items() if v == "DS"], "🔵 FS": [k for k, v in user_scores.items() if v == "FS"], "🟢 FA": [k for k, v in user_scores.items() if v == "FA"]}
    for label, acts in scores_categories.items():
        st.write(f"**{label}:** {', '.join(acts) if acts else '無'}")

    st.divider()
    st.subheader("📊 判定結果")
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    
    matches = []
    for rule in TREATMENT_DATABASE:
        if rule["pair"].issubset(set(da_list)): matches.append(rule)
    if not matches:
        for rule in TREATMENT_DATABASE:
            if rule["pair"].issubset(set(ds_list)): matches.append(rule)

    if matches:
        superficial_res, deep_res = [], []
        for m in matches:
            if m["pair"] in DEEP_PAIRS: deep_res.append(m)
            else: superficial_res.append(m)

        if superficial_res:
            st.markdown("<div class='superficial-header'>🌿 淺層判定</div>", unsafe_allow_html=True)
            for m in superficial_res: st.success(f"**{' + '.join(sorted(list(m['pair'])))}** \n\n {m['result']}")
        if deep_res:
            st.markdown("<div class='deep-header'>💎 深層判定</div>", unsafe_allow_html=True)
            for m in deep_res: st.warning(f"**{' + '.join(sorted(list(m['pair'])))}** \n\n {m['result']}")
    else: st.info("目前組合尚未定義對應筋膜線。")

    st.divider()
    # 上傳按鈕
    if st.button("🚀 完成評估並上傳雲端"):
        if not p_name:
            st.error("請先在『病人資訊』分頁輸入病人姓名！")
        else:
            try:
                new_data = pd.DataFrame([{
                    "日期": str(p_date),
                    "評估人": p_assessor,
                    "病人姓名": p_name,
                    "病歷號": p_id,
                    "DA": ", ".join(da_list) if da_list else "無",
                    "DS": ", ".join(ds_list) if ds_list else "無",
                    "判定結果": " / ".join([m['result'] for m in matches]) if matches else "無結果",
                    "備註": p_note
                }])
                # 這裡 worksheet 名稱必須跟 Google Sheets 標籤名稱完全一致
                existing_data = conn.read(worksheet="Sheet1", usecols=list(range(8)))
                updated_df = pd.concat([existing_data, new_data], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.balloons()
                st.success("✅ 資料已成功同步至 Google Sheets！")
            except Exception as e:
                st.error(f"❌ 上傳失敗。請確認 Secrets 中的試算表網址正確，且該試算表已共用給服務帳號 Email。錯誤: {e}")
