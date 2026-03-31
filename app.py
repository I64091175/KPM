import streamlit as st
from datetime import date

# 1. 基礎網頁設定
st.set_page_config(page_title="KPM 筋膜評估系統", layout="centered")

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

# --- 2. 完整邏輯資料庫 ---
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

# 定義深層判定的組合清單 (用於比對)
DEEP_PAIRS = [
    {"CE", "MSE"},
    {"MSRR", "MSSBL"},
    {"MSRL", "MSSBR"},
    {"CE", "LAU"},
    {"CE", "RAU"},
    {"CRR", "LAD"},
    {"CRL", "RAD"}
]

# --- 3. 介面設計 ---
tab1, tab2, tab3 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果"])

with tab1:
    st.subheader("基本資料紀錄")
    p_name = st.text_input("病人姓名", placeholder="請輸入姓名")
    p_id = st.text_input("病歷號/身分證號", placeholder="請輸入識別碼")
    
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        p_date = st.date_input("評估日期", value=date.today())
    with col_info2:
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
            remark = st.text_input(f"備註 ({act})", key=f"note_{act}", placeholder="特殊表現...")
            user_remarks[act] = remark
            st.divider()

with tab3:
    st.subheader("📋 評分摘要")
    scores_categories = {
        "🔴 DA": [k for k, v in user_scores.items() if v == "DA"],
        "🟠 DS": [k for k, v in user_scores.items() if v == "DS"],
        "🔵 FS": [k for k, v in user_scores.items() if v == "FS"],
        "🟢 FA": [k for k, v in user_scores.items() if v == "FA"]
    }
    for label, acts in scores_categories.items():
        if acts:
            st.write(f"**{label}:** {', '.join(acts)}")
        else:
            st.write(f"**{label}:** 無")

    st.divider()
    st.subheader("📊 判定結果")

    # 邏輯判定：先抓出所有符合規則的組合
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    
    matches = []
    for rule in TREATMENT_DATABASE:
        if rule["pair"].issubset(set(da_list)):
            matches.append(rule)
    if not matches:
        for rule in TREATMENT_DATABASE:
            if rule["pair"].issubset(set(ds_list)):
                matches.append(rule)

    # 2. 進行淺層與深層分類
    if matches:
        superficial_results = []
        deep_results = []

        for m in matches:
            # 檢查目前這個組合是否在定義的深層清單中
            if m["pair"] in DEEP_PAIRS:
                deep_results.append(m)
            else:
                superficial_results.append(m)

        # 顯示淺層判定
        if superficial_results:
            st.markdown("<div class='superficial-header'>🌿 淺層判定</div>", unsafe_allow_html=True)
            for m in superficial_results:
                pair_str = " + ".join(sorted(list(m['pair'])))
                st.success(f"**{pair_str}** \n\n {m['result']}")

        # 顯示深層判定
        if deep_results:
            st.markdown("<div class='deep-header'>💎 深層判定</div>", unsafe_allow_html=True)
            for m in deep_results:
                pair_str = " + ".join(sorted(list(m['pair'])))
                st.warning(f"**{pair_str}** \n\n {m['result']}")
    else:
        st.info("目前組合尚未定義對應筋膜線。")

    st.divider()
    if st.button("完成評估"):
        st.balloons()
        st.success(f"已紀錄：{p_name} ({p_id})")
