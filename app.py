import streamlit as st

# 1. 基礎網頁設定
st.set_page_config(page_title="KPM 筋膜評估系統", layout="centered")

# 調整 CSS 讓按鈕在手機上更顯眼、更好按
st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] { background-color: #f9f9f9; padding: 10px; border-radius: 10px; margin-bottom: 5px; }
    .stHeader { font-size: 1.2rem !important; color: #2c3e50; }
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
    {"pair": {"CRR", "MSSBL"}, "result": "骨盆以上 右側線"},
    {"pair": {"CRL", "MSSBR"}, "result": "骨盆以上 左側線"},
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
    p_note = st.text_area("臨床備註 (主訴、症狀敘述)", height=150)

with tab2:
    st.info("請直接點選下方等級按鈕進行評分")
    
    # 根據圖片定義的所有動作代碼
    actions = [
        "CF", "CE", "CRR", "CRL", 
        "RAU", "RAD", "LAU", "LAD", 
        "MSF", "MSE", "MSRR", "MSRL", 
        "MSSBR", "MSSBL", "CADS"
    ]
    
    user_scores = {}
    
    # 建立按鈕式評分介面
    for act in actions:
        # 使用 segmented_control 做出按鈕組感
        score = st.segmented_control(
            label=f"👉 動作: **{act}**",
            options=["FA", "FS", "DA", "DS"],
            key=f"btn_{act}",
            selection_mode="single",
            default=None
        )
        user_scores[act] = score
        st.write("---") # 分隔線讓手機畫面更清晰

with tab3:
    st.subheader("系統判定報告")
    
    # 整理出 DA 與 DS 的清單
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    
    # 顯示目前偵測到的異常動作
    if da_list:
        st.error(f"⚠️ 偵測到 DA 動作: {', '.join(da_list)}")
    if ds_list:
        st.warning(f"💡 偵測到 DS 動作: {', '.join(ds_list)}")

    final_matches = []
    
    # --- 判定邏輯：以 DA 為最高優先 ---
    # 1. 先掃描符合 DA+DA 的規則
    for rule in TREATMENT_DATABASE:
        if rule["pair"].issubset(set(da_list)):
            final_matches.append({"priority": "🥇 [DA 優先判定]", "data": rule, "color": "blue"})
            
    # 2. 如果完全沒有 DA 符合，才去掃描符合 DS+DS 的規則
    if not final_matches:
        for rule in TREATMENT_DATABASE:
            if rule["pair"].issubset(set(ds_list)):
                final_matches.append({"priority": "🥈 [DS 次要判定]", "data": rule, "color": "orange"})

    # --- 顯示結果清單 ---
    if final_matches:
        for match in final_matches:
            st.markdown(f"### {match['priority']}")
            st.success(f"**結果：{match['data']['result']}**")
            
            # 照片佔位符 (之後上傳照片後可開啟)
            img_filename = f"{match['data']['result']}.jpg"
            st.caption(f"預計顯示圖示: {img_filename}")
    else:
        if not da_list and not ds_list:
            st.info("尚未進行任何評分。")
        else:
            st.info("目前的動作評分組合，在資料庫中尚未定義對應的筋膜線。")

    # 底部功能按鍵
    st.divider()
    if st.button("完成並暫存評估"):
        st.balloons()
        st.success(f"病人 {p_name} 的資料已紀錄。")
