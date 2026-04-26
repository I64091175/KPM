import streamlit as st
from datetime import date, datetime, timedelta, timezone
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px
import google.generativeai as genai  # 新增 Gemini 支援

# --- AI 設定 (依據 SOP: 建議存放在 secrets.toml) ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    # 若本地測試尚未設定 secrets，請在此填入 API Key
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- AI 核心函式 ---
def get_kpm_ai_advice(clinical_summary, extra_info=""):
    """
    KPM-AI 臨床優化版：針對病人產出易懂總結與具體居家運動處方。
    """
    MODEL_NAME = 'models/gemini-2.0-flash'
    
    system_prompt = """
    你是一位專業的 KPM 物理治療師。請根據提供的臨床摘要產出衛教內容。
    【重要指令】：
    1. 絕對禁止使用 #、*、-、> 等 Markdown 符號。
    2. 使用「全形中文符號」如：【】、一、1.、：來排版。
    3. 確保文字在手機記事本中閱讀流暢。
    
    【輸出規範】：
    1. 📋【整體評估總結】：
       - 請用「病人聽得懂」的白話文解釋目前的身體受限狀況。
       - 明確告訴病人：為什麼接下來的運動對他有幫助（例如：調整筋膜張力、釋放關鍵點壓力）。
    
    2. 🧘【居家運動處方】：
       - 針對受限筋膜線（若有 ⭐ 加權項目請優先處理），提供具體的居家運動指導。
       - **必須包含：動作名稱、執行步驟、運動頻率與次數（例如：每組12下，每天3組）。**
    
    3. ⚠️【日常動作禁忌】：
       - 列出該病人在日常生活中（如久坐、搬物）應避免的特定姿勢。
    
    4. 📜【醫囑警語】：
       - 結尾必含：以上建議僅供參考，請由專業物理治療師現場指導。
    """
    
    combined_context = f"評估數據：{clinical_summary}\n備註：{extra_info}"
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(f"{system_prompt}\n\n{combined_context}")
        return response.text if response else "AI 未回傳內容"
    except Exception as e:
        return f"❌ 呼叫失敗: {str(e)}"

def fetch_data_with_buffer(conn):
    """
    優化版抓取：設定 10 秒短快取，避免觸發 Google API 429 限制。
    """
    try:
        # 將 ttl 從 0 改為 10，能有效緩解手機重複點擊的配額消耗
        return conn.read(worksheet="Sheet1", ttl=10)
    except Exception as e:
        if "429" in str(e):
            st.error("⏳ Google 伺服器繁忙 (配額限制)，請稍候 30 秒再試。")
        else:
            st.error(f"❌ 讀取失敗: {str(e)}")
        return pd.DataFrame()

# 1. 基礎設定
st.set_page_config(page_title="KPM 筋膜評估系統 V1.3.21", layout="centered")
tz_taiwan = timezone(timedelta(hours=8))

def fetch_data_no_cache(_conn):
    try:
        return _conn.read(worksheet="Sheet1", ttl=0)
    except:
        return pd.DataFrame()

conn = st.connection("gsheets", type=GSheetsConnection)

# CSS 樣式：確保高度能見度 [cite: 75-81]
st.markdown("""
    <style>
    .action-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 5px; color: #1E88E5; }
    .superficial-header { color: #2E7D32; font-weight: bold; border-left: 5px solid #2E7D32; padding-left: 10px; margin-top: 20px; }
    .superficial-box { border: 2px solid #2E7D32; padding: 15px; border-radius: 8px; background-color: #F1F8E9; margin-bottom: 10px; color: #1B5E20; }
    .deep-box { background-color: #FFF3E0; border-left: 5px solid #EF6C00; padding: 15px; border-radius: 8px; color: #BF360C; margin-bottom: 10px; }
    .priority-box { background-color: #F3E5F5; border: 2px solid #7B1FA2; padding: 15px; border-radius: 8px; color: #4A148C; margin-bottom: 15px; font-weight: bold; }
    .muscle-text { font-weight: bold; color: #D84315; margin-top: 5px; }
    .ankle-box { background-color: #E3F2FD; padding: 15px; border-radius: 8px; border: 2px solid #1E88E5; color: #000000; margin-top: 20px; font-weight: bold; }
    .hist-title { font-size: 1.3rem; font-weight: bold; color: #2c3e50; margin-top: 30px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🩺 KPM 關鍵點評估系統 V1.3.21")

# --- 2. 核心資料定義 --- [cite: 50-67, 81-83]
ACTIONS = ["CF", "CE", "CRR", "CRL", "CR", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS"]
TREATMENT_DATABASE = [
    {"pair": {"CRR", "MSRR"}, "result": "螺旋線 / 骨盆以上 右下到左上後螺旋線", "muscles": "左頭頰、右菱形、右前鉅", "depth": "深層"},
    {"pair": {"CRL", "MSRL"}, "result": "螺旋線 / 骨盆以上 左下到右上後螺旋線", "muscles": "右頭頰、左菱形、左前鉅", "depth": "深層"},
    {"pair": {"LAU", "MSRR"}, "result": "後功能線 / 骨盆以上 左後功能線", "muscles": "左闊背", "depth": "淺層"},
    {"pair": {"RAU", "MSRL"}, "result": "後功能線 / 骨盆以上 右後功能線", "muscles": "右闊背", "depth": "淺層"},
    {"pair": {"MSF", "MSRR"}, "result": "後功能線 / 骨盆以下 右後功能線", "muscles": "右臀大、右股外側", "depth": "淺層"},
    {"pair": {"MSF", "MSRL"}, "result": "後功能線 / 骨盆以下 左後功能線", "muscles": "左臀大、左股外側", "depth": "淺層"},
    {"pair": {"MSE", "MSRR"}, "result": "前功能線 / 骨盆以上 右前功能線", "muscles": "右胸大、右腹直", "depth": "淺層"},
    {"pair": {"MSE", "MSRL"}, "result": "前功能線 / 骨盆以上 左前功能線", "muscles": "左胸大、左腹直", "depth": "淺層"},
    {"pair": {"CF", "MSF"}, "result": "淺背線 / 骨盆以上 淺背線", "muscles": "枕下肌、C7-T1交界", "depth": "深層"},
    {"pair": {"CE", "MSE"}, "result": "深前線 / 骨盆以上 深前線", "muscles": "斜角肌、咀嚼肌", "depth": "深層"},
    {"pair": {"CR", "MSSBL"}, "result": "側線 / 骨盆以上 右側線", "muscles": "右枕骨邊緣/乳突交界、右髂棘上下", "depth": "深層"},
    {"pair": {"CR", "MSSBR"}, "result": "側線 / 骨盆以上 左側線", "muscles": "左枕骨邊緣/乳突交界、左髂棘上下", "depth": "深層"},
    {"pair": {"MSRR", "MSSBL"}, "result": "骨盆以下 右側線或左深前線", "muscles": "加測後判定", "depth": "最後處理"},
    {"pair": {"MSRL", "MSSBR"}, "result": "骨盆以下 左側線或右深前線", "muscles": "加測後判定", "depth": "最後處理"},
    {"pair": {"CE", "LAU"}, "result": "左深前臂線", "muscles": "左深前臂線", "depth": "深層"},
    {"pair": {"CE", "RAU"}, "result": "右深前臂線", "muscles": "右深前臂線", "depth": "深層"},
    {"pair": {"CRR", "LAD"}, "result": "左深後臂線", "muscles": "左深後臂線", "depth": "深層"},
    {"pair": {"CRL", "RAD"}, "result": "右深後臂線", "muscles": "右深後臂線", "depth": "深層"}
]
IMAGE_MAPPING = {"螺旋線": "SPL.jpg", "後功能線": "FF1.jpg", "前功能線": "FF2.jpg", "淺背線": "SBL.jpg", "側線": "LL.jpg", "深前線": "DFL.jpg", "深前臂線": "DFAL.jpg", "深後臂線": "DBAL.jpg"}

def display_ui_common(res_list, title):
    if res_list:
        if title: st.markdown(f"### {title}")
        depth_rank = {"淺層": 0, "深層": 1, "最後處理": 2}
        for res in sorted(res_list, key=lambda x: depth_rank.get(x["depth"], 1)):
            pair_str = " + ".join(sorted(list(res["pair"])))
            if res["is_prio"]:
                st.markdown(f"<div class='priority-box'>🌟 加權重點項目<br>動作組合: {pair_str} ({res['depth']})<br>結果: {res['result']}<br><div class='muscle-text'>💪 建議處理肌肉: {res['muscles']}</div></div>", unsafe_allow_html=True)
            elif res["depth"] == "淺層":
                st.markdown(f"<div class='superficial-header'>🌿 淺層判定</div><div class='superficial-box'><b>動作組合: {pair_str}</b><br>結果: {res['result']}<br><div class='muscle-text'>💪 建議處理肌肉: {res['muscles']}</div></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='deep-box'><strong>💎 深層判定</strong><br>動作組合: {pair_str}<br>結果: {res['result']}<br><div class='muscle-text'>💪 建議處理肌肉: {res['muscles']}</div></div>", unsafe_allow_html=True)
            imgs = [v for k, v in IMAGE_MAPPING.items() if k in res['result']]
            if imgs:
                with st.expander(f"🔍 檢視圖譜"):
                    for img in imgs: st.image(f"images/{img}", width=350)

# --- 3. 介面分頁 ---

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📋 基本資料", 
    "🦴 主動快篩", 
    "📊 判定結果", 
    "📚 完整圖譜", 
    "📈 趨勢追蹤",
    "🤖 AI 助手"
])

with tab1:
    st.subheader("👤 基本資料")
    p_name = st.text_input("病人姓名", key="p_name")
    p_id = st.text_input("病歷號", key="p_id")
    p_date = st.date_input("評估日期", value=datetime.now(tz_taiwan).date())
    vas_score = st.slider("🤒 病人自覺整體分數 (10分最痛)", 0, 10, 5)
    p_assessor = st.text_input("評估人")
    p_note = st.text_area("整體臨床總結備註")

with tab2:
    st.info("請標註評估等級。核心受限請點選 ⭐ 加權。")
    user_scores, user_action_notes, user_priorities = {}, {}, {}
    for i, act in enumerate(ACTIONS, 1):
        st.markdown(f"<div class='action-title'>{i}. 動作: {act}</div>", unsafe_allow_html=True)
        c1, c2 = st.columns([3, 1])
        user_scores[act] = c1.segmented_control(label=act, options=["FA", "FS", "DS", "DA"], key=f"s_{act}", selection_mode="single", label_visibility="collapsed")
        user_priorities[act] = c2.checkbox("⭐ 加權", key=f"prio_{act}")
        user_action_notes[act] = st.text_input(f"備註 ({act})", key=f"note_{act}")
        st.divider()

with tab3:
    st.subheader("📊 判定結果")
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    priority_list = [k for k, v in user_priorities.items() if v]

    if da_list or ds_list:
        st.write(f"🛑 **DA:** {', '.join(da_list) if da_list else '無'} | ⚠️ **DS:** {', '.join(ds_list) if ds_list else '無'}")
        if priority_list: st.write(f"🌟 **關鍵加權點:** {', '.join(priority_list)}")
        st.divider()

    weighted_res, da_da_res, ds_ds_res = [], [], []
    for rule in TREATMENT_DATABASE:
        s1, s2 = user_scores.get(list(rule["pair"])[0]), user_scores.get(list(rule["pair"])[1])
        if s1 and s2 and s1 == s2 and s1 in ["DA", "DS"]:
            item = {**rule, "grade": s1, "is_prio": not rule["pair"].isdisjoint(set(priority_list))}
            if item["is_prio"]: weighted_res.append(item)
            elif s1 == "DA": da_da_res.append(item)
            else: ds_ds_res.append(item)

    display_ui_common(weighted_res, "⭐ 加權重點對應")
    display_ui_common(da_da_res, "🟦 DA-DA 對應結果")
    display_ui_common(ds_ds_res, "🟧 DS-DS 對應結果")

    # --- 【新增邏輯：彙整建議處理肌肉字串】 ---
    all_matched_items = weighted_res + da_da_res + ds_ds_res
    # 提取所有 matched rule 裡的 muscle，並轉為去重複的清單
    suggested_muscles = []
    for item in all_matched_items:
        m_val = item.get("muscles")
        if m_val:
            if isinstance(m_val, list):
                # 如果未來你改成 list 格式，這行能處理
                suggested_muscles.extend(m_val)
            else:
                # 處理目前的字串格式 (如: "左頭頰、右菱形")
                # 先依據「、」或「,」拆分，確保去重複效果精準
                parts = str(m_val).replace('、', ',').split(',')
                suggested_muscles.extend([p.strip() for p in parts])
    
    # 去重複並用逗號隔開
    if suggested_muscles:
        unique_muscles_str = "、".join(sorted(list(set(suggested_muscles))))
    else:
        unique_muscles_str = "無資料"
    # 動態紀錄加測結果
    selected_ankle_options = []
    all_pairs = [" + ".join(sorted(list(r["pair"]))) for r in all_matched_items]
    for p_str in ["MSRR + MSSBL", "MSRL + MSSBR"]:
        if p_str in all_pairs:
            st.markdown(f"<div class='ankle-box'>🔍 偵測到 {p_str} 相對應，請加測：</div>", unsafe_allow_html=True)
            side = "右" if "MSRR" in p_str else "左"
            opp = "左" if side == "右" else "右"
            
            l1, l2 = f"{side}踝內翻受限 (處理{side}側線)", f"{opp}踝外翻受限 (處理{opp}深前線)"
            if st.checkbox(l1, key=f"save_ak1_{p_str}"): selected_ankle_options.append(l1)
            if st.checkbox(l2, key=f"save_ak2_{p_str}"): selected_ankle_options.append(l2)

    st.divider()
    if st.button("🚀 完成評估並同步雲端"):
        if not p_name or not p_id: st.error("請輸入姓名與病歷號！")
        else:
            try:
                # 整合加測建議紀錄 
                ankle_final_str = ""
                triggered_ankle_pairs = [p for p in ["MSRR + MSSBL", "MSRL + MSSBR"] if p in all_pairs]
                if triggered_ankle_pairs:
                    base_prompt = f"偵測到 {'、'.join(triggered_ankle_pairs)} 相對應。"
                    if selected_ankle_options:
                        ankle_final_str = f"{base_prompt}加測結果：{'、'.join(selected_ankle_options)}"
                    else:
                        ankle_final_str = f"{base_prompt}尚未勾選加測結果。"

                act_notes = [f"{a}:{user_action_notes[a].strip()}" for a in ACTIONS if user_action_notes[a].strip()]
                prio_tags = [f"{a}(⭐)" for a in priority_list]
                combined_details = "/".join(act_notes + prio_tags)
                final_note = f"{p_note} | 詳細: {combined_details}" if p_note and combined_details else (p_note or combined_details)
                
                now_tw = datetime.now(tz_taiwan)
                final_dt_str = now_tw.strftime("%Y-%m-%d %H:%M") if p_date >= now_tw.date() else f"{p_date} (補)"
                
                # --- 【核心修正：將肌肉與衛教欄位加入 record 字典】 ---
                record = {
                    "日期": final_dt_str, 
                    "評估人": p_assessor, 
                    "病人姓名": p_name, 
                    "病歷號": f"'{p_id}",
                    "病人自覺分數": vas_score, 
                    "加權關鍵點": ", ".join(priority_list),
                    "判定結果": " / ".join([res['result'] for res in all_matched_items]), 
                    "建議處理肌肉": unique_muscles_str, # <--- 修正點 1
                    "備註": final_note, 
                    "加測建議": ankle_final_str,
                    "AI衛教建議": ""                  # <--- 修正點 2 (預留位置)
                }
                
                # 更新動作分數
                record.update(user_scores)
                
                # 抓取雲端資料並合併
                df_old = fetch_data_no_cache(conn)
                df_final = pd.concat([df_old, pd.DataFrame([record])], ignore_index=True)
                
                # 同步回 Google Sheets
                conn.update(worksheet="Sheet1", data=df_final)
                
                st.success(f"✅ 資料已同步！時間：{final_dt_str}")
                st.balloons()
            except Exception as e:
                st.error(f"同步失敗: {e}")

with tab4:
    st.subheader("📚 完整圖譜")
    atlas = {"FF 功能線": ["FF1.jpg", "FF2.jpg"], "SBL 淺背線": ["SBL.jpg"], "SFL 淺前線": ["SFL.jpg"], "LL 側線": ["LL.jpg"], "SPL 螺旋線": ["SPL.jpg"], "DFL 深前線": ["DFL.jpg"], "手臂線系列": ["SFAL.jpg", "SBAL.jpg", "DFAL.jpg", "DBAL.jpg"]}
    for title, imgs in atlas.items():
        with st.expander(f"📍 {title}"):
            for img in imgs: st.image(f"images/{img}", use_container_width=True)

with tab5:
    st.subheader("📈 趨勢追蹤")
    search_id = st.text_input("🔍 輸入病歷號查詢歷史紀錄", key="q_id_v12_final")
    
    if search_id:
        all_df = fetch_data_no_cache(conn)
        if not all_df.empty:
            all_df['病歷號'] = all_df['病歷號'].astype(str).str.lstrip("'").str.strip()
            p_history = all_df[all_df["病歷號"] == str(search_id).strip()].copy()
            
            if not p_history.empty:
                p_history['sort_dt'] = pd.to_datetime(p_history['日期'].str.replace(" (補)", ""), errors='coerce')
                p_history = p_history.sort_values("sort_dt")
                last_record = p_history.iloc[-1]
                
                st.markdown(f"<div class='hist-title'>📋 末次評估詳情 ({last_record['日期']})</div>", unsafe_allow_html=True)
                
                last_scores = {a: last_record.get(a, "FA") for a in ACTIONS}
                last_priorities = str(last_record.get("加權關鍵點", "")).split(", ")
                
                h_weighted, h_da, h_ds = [], [], []
                for rule in TREATMENT_DATABASE:
                    acts = list(rule["pair"])
                    s1, s2 = last_scores.get(acts[0]), last_scores.get(acts[1])
                    if s1 and s2 and s1 == s2 and s1 in ["DA", "DS"]:
                        item = {**rule, "is_prio": not rule["pair"].isdisjoint(set(last_priorities))}
                        if item["is_prio"]: h_weighted.append(item)
                        elif s1 == "DA": h_da.append(item)
                        else: h_ds.append(item)

                display_ui_common(h_weighted, "⭐ 上次加權重點")
                display_ui_common(h_da, "🟦 上次 DA-DA 對應")
                display_ui_common(h_ds, "🟧 上次 DS-DS 對應")
                
                if "加測建議" in last_record and pd.notna(last_record["加測建議"]) and last_record["加測建議"] != "":
                    st.markdown(f"<div class='ankle-box'>ℹ️ 歷史紀錄加測結果：<br>{last_record['加測建議']}</div>", unsafe_allow_html=True)

                st.divider()
                st.markdown("### 🤒 疼痛分數演變趨勢")
                fig_bar = px.bar(p_history.tail(6), x="日期", y="病人自覺分數", color_discrete_sequence=["#1E88E5"], text_auto=True)
                fig_bar.update_layout(xaxis_type='category') # 修正時間軸問題
                st.plotly_chart(fig_bar, use_container_width=True)
                
                with st.expander("📂 查看所有歷史筆記"):
                    display_cols = ["日期", "判定結果", "病人自覺分數", "備註"]
                    if "加測建議" in p_history.columns: display_cols.insert(2, "加測建議")
                    st.dataframe(p_history.sort_values("sort_dt", ascending=False)[display_cols])
            else: st.error("找不到此病歷號")
        else: st.warning("資料庫目前為空。")

with tab6:
    st.header("🤖 AI 臨床衛教助手")
    ai_mode = st.radio("功能選擇", ["🔍 抓取最後一次評估結果", "✍️ 手動輸入狀況分析"])
    
    st.markdown("---")
    extra_note = st.text_area("📝 治療師額外補充資訊", placeholder="例如：加強核心訓練、病人希望能在家做的運動不要超過10分鐘...")

    if ai_mode == "🔍 抓取最後一次評估結果":
        search_id = st.text_input("請輸入病歷號進行檢索", key="ai_search_id")
        
        if st.button("檢索並生成建議"):
            with st.spinner("正在搜尋雲端最新資料..."):
                df_history = fetch_data_with_buffer(conn)
                if not df_history.empty:
                    # 標題清洗
                    df_history.columns = df_history.columns.str.strip().str.replace('\n', '')
                    col_pid = next((c for c in df_history.columns if "病歷號" in c), None)
                    col_date = next((c for c in df_history.columns if "日期" in c), None)
                    col_ai_record = next((c for c in df_history.columns if "AI衛教建議" in c), None)
                    
                    if col_pid:
                        df_history["pid_clean"] = df_history[col_pid].astype(str).str.lstrip("'").str.strip()
                        p_data = df_history[df_history["pid_clean"] == str(search_id).strip()].copy()
                        
                        if not p_data.empty:
                            p_data[col_date] = pd.to_datetime(p_data[col_date], errors='coerce')
                            latest_record = p_data.sort_values(by=col_date, ascending=False).iloc[0]
                            
                            # Q3 邏輯：檢查資料庫是否已有 AI 建議
                            existing_advice = latest_record.get(col_ai_record, "") if col_ai_record else ""
                            
                            if existing_advice and len(str(existing_advice)) > 50:
                                st.session_state.generated_advice = existing_advice
                                st.info("💡 已從雲端資料庫讀取現有衛教資訊（節省流量）。")
                            else:
                                # 提取建議肌肉 (Q2 重要性)
                                muscle_info = latest_record.get('建議處理肌肉', '無資料')
                                clinical_context = f"判定: {latest_record.get('判定結果', '無')}, 肌肉: {muscle_info}"
                                st.session_state.generated_advice = get_kpm_ai_advice(clinical_context, extra_note)
                                st.warning("🆕 雲端無舊紀錄，已產生新 AI 衛教。")
                            
                            st.success("✅ 處理完成")
                        else:
                            st.error("找不到該病歷號")

    else: # 手動輸入模式
        manual_context = st.text_area("請輸入臨床描述")
        if st.button("生成分析建議"):
            st.session_state.generated_advice = get_kpm_ai_advice(manual_context, extra_note)

    # 顯示結果與優化複製
    if 'generated_advice' in st.session_state and st.session_state.generated_advice:
        st.markdown("---")
        st.subheader("📋 KPM AI 運動建議")
        
        # Q1 效果：顯示與複製框
        st.info("以下內容可直接複製")
        st.code(st.session_state.generated_advice, language="text")
        
        # 額外提供一個「存回雲端」按鈕 (選填)
        if st.button("💾 將此建議同步至雲端資料庫"):
            st.toast("此功能需要配合 GSheets Update 權限，目前建議先手動複製。")

# 時區顯示 (依據 SOP 要求)
st.caption(f"系統時間：{datetime.now(tz_taiwan).strftime('%Y-%m-%d %H:%M:%S')} (Taipei)")
