import streamlit as st

# 1. 基礎網頁設定
st.set_page_config(page_title="KPM 筋膜評估系統", layout="centered")

# CSS 優化：讓按鈕組與備註框更像一個整體的「卡片」
st.markdown("""
    <style>
    .stHeader { font-size: 1.2rem !important; color: #2c3e50; }
    .action-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 5px; color: #1E88E5; }
    /* 調整分隔線顏色 */
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

# --- 3. 介面設計 ---
tab1, tab2, tab3 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果"])

with tab1:
    st.subheader("基本資料紀錄")
    p_name = st.text_input("病人姓名", placeholder="請輸入姓名")
    p_id = st.text_input("病歷號/身分證號", placeholder="請輸入識別碼")
    p_note = st.text_area("整體臨床總結備註", height=100)

with tab2:
    st.info("請直接點選等級按鈕，並可在下方輸入特殊標註")
    
    actions = [
        "CF", "CE", "CRR", "CRL", 
        "RAU", "RAD", "LAU", "LAD", 
        "MSF", "MSE", "MSRR", "MSRL", 
        "MSSBR", "MSSBL", "CADS", "CR"
    ]
    
    user_scores = {}
    user_remarks = {} 
    
    # 使用 Container 建立更美觀的動作區塊
    for i, act in enumerate(actions, 1):
        with st.container():
            # 動作標題與按鈕
            st.markdown(f"<div class='action-title'>{i}. 動作: {act}</div>", unsafe_allow_html=True)
            
            score = st.segmented_control(
                label=f"score_{act}",
                options=["FA", "FS", "DA", "DS"],
                key=f"btn_{act}",
                selection_mode="single",
                default=None,
                label_visibility="collapsed"
            )
            user_scores[act] = score
            
            # 備註輸入欄
            remark = st.text_input(f"備註 ({act})", key=f"note_{act}", placeholder="輸入特殊表現...")
            user_remarks[act] = remark
            
            # 加入明顯的分隔線
            st.divider()

with tab3:
    st.subheader("系統判定報告")
    
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    
    final_matches = []
    
    # 邏輯判定
    for rule in TREATMENT_DATABASE:
        if rule["pair"].issubset(set(da_list)):
            final_matches.append(rule)
            
    if not final_matches:
        for rule in TREATMENT_DATABASE:
            if rule["pair"].issubset(set(ds_list)):
                final_matches.append(rule)

    # 顯示結果
    if final_matches:
        for match in final_matches:
            pair_string = " + ".join(sorted(list(match['pair'])))
            st.success(f"### {pair_string} \n **{match['result']}**")
            
            for act in match['pair']:
                if user_remarks[act]:
                    st.caption(f"💡 {act} 備註: {user_remarks[act]}")
    else:
        if not da_list and not ds_list:
            st.info("尚未進行任何評分。")
        else:
            st.info("目前的動作評分組合尚未定義對應的筋膜線。")

    st.divider()
    if st.button("完成並暫存評估"):
        st.balloons()
        st.success(f"病人 {p_name} 的資料已紀錄。")
