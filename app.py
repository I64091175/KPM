import streamlit as st

# 1. 基礎設定
st.set_page_config(page_title="關鍵點評估系統", layout="centered")

# 讓手機介面的按鈕大一點
st.markdown("""
    <style>
    .stSelectbox div[data-baseweb="select"] { font-size: 1.1rem; }
    .stButton>button { width: 100%; height: 3em; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🩺 關鍵點評估系統")

# --- 2. 邏輯資料庫 (請根據你的圖片繼續增加) ---
# 這裡定義：哪些動作組合(DA+DA)對應到什麼結果與照片
TREATMENT_DATABASE = [
    {"pair": {"CF", "MSF"}, "result": "骨盆以上 淺背線", "info": "檢查後側筋膜張力，建議處理 SBL 線路。", "img": "sbl.jpg"},
    {"pair": {"CE", "MSE"}, "result": "骨盆以上 深前線", "info": "核心深層穩定不足，建議處理 DFL 線路。", "img": "dfl.jpg"},
    {"pair": {"CRR", "MSRR"}, "result": "骨盆以上 右下到左上後螺旋線", "info": "軀幹旋轉受限，注意螺旋線交叉點。", "img": "spl_r.jpg"},
    {"pair": {"CRL", "MSRL"}, "result": "骨盆以上 左下到右上後螺旋線", "info": "軀幹旋轉受限，注意螺旋線交叉點。", "img": "spl_l.jpg"},
    {"pair": {"LAU", "MSRR"}, "result": "骨盆以上 左後功能線", "info": "對側動力鍊失衡，檢查後功能線。", "img": "bfl.jpg"},
    # ... 你可以照格式繼續貼上圖片中的其他 10 幾條邏輯
]

# --- 3. 介面分頁 ---
tab1, tab2, tab3 = st.tabs(["👤 病人資訊", "📝 10項評估", "📊 分析報告"])

with tab1:
    st.subheader("基本資料")
    p_name = st.text_input("病人姓名")
    p_id = st.text_input("病歷號")
    p_note = st.text_area("臨床備註 (如：主訴、過去病史)", height=150)

with tab2:
    st.subheader("動作評分 (FA/FS/DA/DS)")
    # 定義你要評估的 10 個核心動作
    actions = ["CF", "CE", "CRR", "CRL", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL"]
    
    # 建立評分儲存空間
    user_scores = {}
    
    # 使用 2 欄佈局讓手機畫面不至於太長
    col_a, col_b = st.columns(2)
    for i, act in enumerate(actions):
        target_col = col_a if i % 2 == 0 else col_b
        user_scores[act] = target_col.selectbox(
            f"動作: {act}", 
            ["-", "FA", "FS", "DA", "DS"], 
            key=f"act_{act}"
        )

with tab3:
    st.subheader("評估結果與處置")
    
    # 提取評分為 DA 與 DS 的清單
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    
    st.write(f"**偵測到 DA:** {', '.join(da_actions) if (da_actions := da_list) else '無'}")
    
    final_matches = []
    
    # --- 關鍵邏輯：以 DA 為優先 ---
    # 先找 DA 的組合
    for rule in TREATMENT_DATABASE:
        if rule["pair"].issubset(set(da_list)):
            final_matches.append({"type": "DA 優先判定", "data": rule})
            
    # 如果 DA 沒配對到，再找 DS 的組合
    if not final_matches:
        for rule in TREATMENT_DATABASE:
            if rule["pair"].issubset(set(ds_list)):
                final_matches.append({"type": "DS 次要判定", "data": rule})

    # --- 顯示判定結果 ---
    if final_matches:
        for match in final_matches:
            with st.expander(f"🚩 {match['type']}: {match['data']['result']}", expanded=True):
                st.info(match['data']['info'])
                # 顯示預設照片 (如果檔案存在的話)
                try:
                    # st.image(match['data']['img'], caption=match['data']['result'])
                    st.warning(f"請在資料夾放一張名為 {match['data']['img']} 的照片即可顯示圖示")
                except:
                    st.error("找不到照片檔案")
    else:
        st.info("目前的評分組合尚未觸發特定的筋膜鍊判定。")

    # 儲存與匯出 (模擬)
    if st.button("完成評估並儲存"):
        st.balloons()
        st.success(f"病人 {p_name} 的資料已暫存。")
        # 這裡未來可以加入寫入 CSV 或 Google Sheets 的代碼