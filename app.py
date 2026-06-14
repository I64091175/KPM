import os
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



def load_local_text_file(file_name):
    """
    安全讀取本地 UTF-8 檔案的防呆副程式
    """
    if os.path.exists(file_name):
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            st.error(f"讀取 {file_name} 時發生編碼錯誤: {str(e)}")
            return ""
    else:
        st.error(f"找不到關鍵核心檔案: {file_name}，請確認檔案是否在同資料夾下！")
        return ""


def get_kpm_ai_advice(clinical_summary, extra_info=""):
    """
    KPM-AI 優化版：動態加載本地 RAG 知識庫與 SOP 死命令    
    """
    # 1. 自動從本地加載死命令與運動資料庫
    sop_rules = load_local_text_file("kpm_ai_sop.txt")
    knowledge_base = load_local_text_file("kpm_knowledge_base.txt")
    
    if not sop_rules or not knowledge_base:
        return "系統錯誤：後台安全知識庫加載失敗，請通知治療師工程師檢查本地文字檔。"

    # 2. 將規則與資料庫融合，封鎖成絕對的解耦邊界（System Instruction）
    full_system_context = f"{sop_rules}\n\n【臨床運作專家衛教資料庫內文如下】：\n{knowledge_base}"
    
    # 3. 您的可用備援輪詢模型清單（維持 V1.3.23 穩定性規範）
    fallback_models = [
        'models/gemini-1.5-flash-latest', 
        'models/gemini-2.0-flash-lite-001',
        'models/gemini-1.5-flash',
        'models/gemini-flash-latest',
        'models/gemini-pro-latest'
    ]
    # 4. 準備發送給 AI 的使用者輸入（包含快篩數據與主訴備註）
    user_prompt = f"以下為當前病患的臨床判定數據與備註，請立即執行黃金 3 招 HEP 輸出：\n{clinical_summary}\n補充狀況：{extra_info}"

    # 5. 自動輪詢切換（Auto-Fallback）執行
    for model_name in fallback_models:
        try:
            # 使用最新版 SDK 的 system_instruction 參數傳入邊界，達到最高抗幻覺效果
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=full_system_context
            )
            
            # 設定合適的溫度（建議 0.2-0.3），讓 AI 嚴格抓取資料庫，不天馬行空
            response = model.generate_content(
                user_prompt,
                generation_config={"temperature": 0.2}
            )
            return response.text
            
        except Exception as e:
            # 如果當前模型超流或限額，自動記錄並切換到下一個備援模型
            continue
            
    return "❌ 所有備援模型皆暫時無法回應，請確認您的 GOOGLE_API_KEY 狀態或網路連線。"


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
st.set_page_config(page_title="KPM 筋膜評估系統 V1.4", layout="centered")
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

st.title("🩺 KPM 關鍵點評估系統 V1.4")

# --- 2. 核心資料定義 --- [cite: 50-67, 81-83]
ACTIONS = ["CF", "CE", "CRR", "CRL", "CR", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS"]
TREATMENT_DATABASE = [
    # --- 螺旋線 (Spiral Line) ---
    {
        "pair": {"CRR", "MSRR"}, 
        "result": "螺旋線 / 骨盆以上 右下到左上後螺旋線", 
        "muscles": "左頭頰、右菱形、右前鉅", 
        "depth": "深層",
        "line_code": "SPL",
        "anatomy_train": "Spiral Line"
    },
    {
        "pair": {"CRL", "MSRL"}, 
        "result": "螺旋線 / 骨盆以上 左下到右上後螺旋線", 
        "muscles": "右頭頰、左菱形、左前鉅", 
        "depth": "深層",
        "line_code": "SPL",
        "anatomy_train": "Spiral Line"
    },

    # --- 後功能線 (Posterior Functional Line) ---
    {
        "pair": {"LAU", "MSRR"}, 
        "result": "後功能線 / 骨盆以上 左後功能線", 
        "muscles": "左闊背", 
        "depth": "淺層",
        "line_code": "FF1",
        "anatomy_train": "Functional Line"
    },
    {
        "pair": {"RAU", "MSRL"}, 
        "result": "後功能線 / 骨盆以上 右後功能線", 
        "muscles": "右闊背", 
        "depth": "淺層",
        "line_code": "FF1",
        "anatomy_train": "Functional Line"
    },
    {
        "pair": {"MSF", "MSRR"}, 
        "result": "後功能線 / 骨盆以下 右後功能線", 
        "muscles": "右臀大、右股外側", 
        "depth": "淺層",
        "line_code": "FF1",
        "anatomy_train": "Functional Line"
    },
    {
        "pair": {"MSF", "MSRL"}, 
        "result": "後功能線 / 骨盆以下 左後功能線", 
        "muscles": "左臀大、左股外側", 
        "depth": "淺層",
        "line_code": "FF1",
        "anatomy_train": "Functional Line"
    },

    # --- 前功能線 (Anterior Functional Line) ---
    {
        "pair": {"MSE", "MSRR"}, 
        "result": "前功能線 / 骨盆以上 右前功能線", 
        "muscles": "右胸大、右腹直", 
        "depth": "淺層",
        "line_code": "FF2",
        "anatomy_train": "Functional Line"
    },
    {
        "pair": {"MSE", "MSRL"}, 
        "result": "前功能線 / 骨盆以上 左前功能線", 
        "muscles": "左胸大、左腹直", 
        "depth": "淺層",
        "line_code": "FF2",
        "anatomy_train": "Functional Line"
    },

    # --- 淺背線 & 深前線 (SBL & DFL) ---
    {
        "pair": {"CF", "MSF"}, 
        "result": "淺背線 / 骨盆以上 淺背線", 
        "muscles": "枕下肌、C7-T1交界", 
        "depth": "深層",
        "line_code": "SBL",
        "anatomy_train": "Superficial Back Line"
    },
    {
        "pair": {"CE", "MSE"}, 
        "result": "深前線 / 骨盆以上 深前線", 
        "muscles": "斜角肌、咀嚼肌", 
        "depth": "深層",
        "line_code": "DFL",
        "anatomy_train": "Deep Front Line"
    },

    # --- 側線 (Lateral Line) ---
    {
        "pair": {"CR", "MSSBL"}, 
        "result": "側線 / 骨盆以上 右側線", 
        "muscles": "右枕骨邊緣/乳突交界、右髂棘上下", 
        "depth": "深層",
        "line_code": "LL",
        "anatomy_train": "Lateral Line"
    },
    {
        "pair": {"CR", "MSSBR"}, 
        "result": "側線 / 骨盆以上 左側線", 
        "muscles": "左枕骨邊緣/乳突交界、左髂棘上下", 
        "depth": "深層",
        "line_code": "LL",
        "anatomy_train": "Lateral Line"
    },

    # --- 骨盆以下特殊加測區 (Ankle Trigger) ---
    {
        "pair": {"MSRR", "MSSBL"}, 
        "result": "骨盆以下 右側線或左深前線", 
        "muscles": "需依踝部加測判定", 
        "depth": "最後處理",
        "require_ankle_check": True,
        "anatomy_train": "LL/DFL Interaction"
    },
    {
        "pair": {"MSRL", "MSSBR"}, 
        "result": "骨盆以下 左側線或右深前線", 
        "muscles": "需依踝部加測判定", 
        "depth": "最後處理",
        "require_ankle_check": True,
        "anatomy_train": "LL/DFL Interaction"
    },

    # --- 深層臂線 (Deep Arm Lines) ---
    {
        "pair": {"CE", "LAU"}, 
        "result": "左深前臂線", 
        "muscles": "左深前臂線關鍵點", 
        "depth": "深層",
        "line_code": "DFAL",
        "anatomy_train": "Deep Front Arm Line"
    },
    {
        "pair": {"CE", "RAU"}, 
        "result": "右深前臂線", 
        "muscles": "右深前臂線關鍵點", 
        "depth": "深層",
        "line_code": "DFAL",
        "anatomy_train": "Deep Front Arm Line"
    },
    {
        "pair": {"CRR", "LAD"}, 
        "result": "左深後臂線", 
        "muscles": "左深後臂線關鍵點", 
        "depth": "深層",
        "line_code": "DBAL",
        "anatomy_train": "Deep Back Arm Line"
    },
    {
        "pair": {"CRL", "RAD"}, 
        "result": "右深後臂線", 
        "muscles": "右深後臂線關鍵點", 
        "depth": "深層",
        "line_code": "DBAL",
        "anatomy_train": "Deep Back Arm Line"
    }
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
    
    # 1. 基礎資料篩選與摘要顯示
    da_list = [k for k, v in user_scores.items() if v == "DA"]
    ds_list = [k for k, v in user_scores.items() if v == "DS"]
    priority_list = [k for k, v in user_priorities.items() if v]

    if da_list or ds_list:
        st.write(f"🛑 **DA:** {', '.join(da_list) if da_list else '無'} | ⚠️ **DS:** {', '.join(ds_list) if ds_list else '無'}")
        if priority_list: 
            st.write(f"🌟 **關鍵加權點:** {', '.join(priority_list)}")
        st.divider()

    # 2. 核心判定配對邏輯 (遵守同級對應原則)
    weighted_res, da_da_res, ds_ds_res = [], [], []
    for rule in TREATMENT_DATABASE:
        pair_elements = list(rule["pair"])
        s1, s2 = user_scores.get(pair_elements[0]), user_scores.get(pair_elements[1])
        
        # 必須 A 與 B 同為 DA 或同時為 DS 才能觸發判定 [cite: 14]
        if s1 and s2 and s1 == s2 and s1 in ["DA", "DS"]:
            # 判斷是否包含加權項目 
            is_prio = not rule["pair"].isdisjoint(set(priority_list))
            item = {**rule, "grade": s1, "is_prio": is_prio}
            
            if is_prio: 
                weighted_res.append(item)
            elif s1 == "DA": 
                da_da_res.append(item)
            else: 
                ds_ds_res.append(item)

    # 3. 視覺化結果呈現 (排序：加權 > DA > DS) 
    display_ui_common(weighted_res, "⭐ 加權重點對應")
    display_ui_common(da_da_res, "🟦 DA-DA 對應結果")
    display_ui_common(ds_ds_res, "🟧 DS-DS 對應結果")

    # 4. 建議處理肌肉彙整 (去重複)
    all_matched_items = weighted_res + da_da_res + ds_ds_res
    suggested_muscles = []
    for item in all_matched_items:
        m_val = item.get("muscles")
        if m_val:
            # 處理字串格式並統一分隔符號
            parts = str(m_val).replace('、', ',').split(',')
            suggested_muscles.extend([p.strip() for p in parts if p.strip()])
    
    unique_muscles_str = "、".join(sorted(list(set(suggested_muscles)))) if suggested_muscles else "無資料"

    # 5. 踝部加測互動 UI [cite: 16, 20]
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

    # 6. 雲端同步儲存邏輯 [cite: 14, 17]
    st.divider()
    if st.button("🚀 完成評估並同步雲端", use_container_width=True):
        if not p_name or not p_id: 
            st.error("請輸入姓名與病歷號！")
        else:
            try:
                # A. 整合加測備註
                ankle_final_str = ""
                triggered_ankle_pairs = [p for p in ["MSRR + MSSBL", "MSRL + MSSBR"] if p in all_pairs]
                if triggered_ankle_pairs:
                    base_prompt = f"偵測到 {'、'.join(triggered_ankle_pairs)} 相對應。"
                    ankle_final_str = f"{base_prompt}加測結果：{'、'.join(selected_ankle_options)}" if selected_ankle_options else f"{base_prompt}尚未勾選加測結果。"

                # B. 整合備註與動作細節
                act_notes = [f"{a}:{user_action_notes[a].strip()}" for a in ACTIONS if user_action_notes[a].strip()]
                prio_tags = [f"{a}(⭐)" for a in priority_list]
                combined_details = "/".join(act_notes + prio_tags)
                final_note = f"{p_note} | 詳細: {combined_details}" if p_note and combined_details else (p_note or combined_details)
                
                # C. 時間戳記處理 (自動標記補登) 
                now_tw = datetime.now(tz_taiwan)
                final_dt_str = now_tw.strftime("%Y-%m-%d %H:%M") if p_date >= now_tw.date() else f"{p_date} (補)"
                
                # D. 建構紀錄字典
                record = {
                    "日期": final_dt_str, 
                    "評估人": p_assessor, 
                    "病人姓名": p_name, 
                    "病歷號": f"'{p_id}", # 強制 Excel 為文字格式
                    "病人自覺分數": vas_score, 
                    "加權關鍵點": ", ".join(priority_list),
                    "判定結果": " / ".join([res['result'] for res in all_matched_items]), 
                    "建議處理肌肉": unique_muscles_str,
                    "備註": final_note, 
                    "加測建議": ankle_final_str,
                    "AI衛教建議": "" # 預留給未來 AI Agent
                }
                record.update(user_scores) # 加入所有主動測試分數
                
                # E. 同步至 Google Sheets 
                df_old = fetch_data_no_cache(conn)
                df_final = pd.concat([df_old, pd.DataFrame([record])], ignore_index=True)
                conn.update(worksheet="Sheet1", data=df_final)
                
                st.success(f"✅ 資料已成功同步！系統時間：{final_dt_str}")
                st.balloons()
            except Exception as e:
                st.error(f"❌ 同步失敗: {str(e)}")

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
    
    # 將功能 radio 升級為滿足三大臨床場景的三合一核心模式
    ai_mode = st.radio(
        "功能選擇", 
        ["⚡ 根據當前評估一鍵生成", "🔍 抓取歷史評估結果", "✍️ 手動輸入狀況分析"]
    )
    
    st.markdown("---")
    
    # 統一收集治療師的客製化補充資訊（醫從性微調核心）
    extra_note = st.text_area(
        "📝 治療師額外補充資訊", 
        placeholder="例如：病人為高齡長輩、希望在家做的運動不要超過10分鐘、加強核心穩定..."
    )

    # 處理模式一：當前即時評估一鍵生成（最適合常態一對一門診完結時使用）
    if ai_mode == "⚡ 根據當前評估一鍵生成":
        st.subheader("🧘 客製化居家衛教處方即時生成")
        
        # 安全防呆機制：確保前幾頁 (Tab 2/Tab 3) 已有快篩結果，若無則給予提示
        if 'da_list' in locals() and 'ds_list' in locals():
            # 將前幾頁算好的即時列表，整理為符合 KPM 動力鏈分析的格式化字串
            判定結果總覽 = f"功能異常且無症狀(DA)項目: {', '.join(da_list)}\n功能異常且有症狀(DS)項目: {', '.join(ds_list)}"
            
            if st.button("🚀 根據當前評估一鍵生成衛教單", key="btn_live_generate"):
                with st.spinner("KPM-AI 正在對照專家資料庫，進行跨線路動態組裝中..."):
                    # 調用解耦的核心函式，傳入即時數據與補充備註
                    st.session_state.generated_advice = get_kpm_ai_advice(
                        clinical_summary=判定結果總覽, 
                        extra_info=extra_note
                    )
                st.success("✅ 即時衛教單組裝完成！")
        else:
            st.warning("⚠️ 系統偵測到當前診次尚未完成動作快篩評估，請先至前方的評估分頁輸入數據。")

    # 處理模式二：抓取雲端歷史紀錄（最適合複診調閱、補發衛教單場景）
    elif ai_mode == "🔍 抓取歷史評估結果":
        search_id = st.text_input("請輸入病歷號進行檢索", key="ai_search_id")
        
        if st.button("檢索並生成建議", key="btn_history_fetch"):
            with st.spinner("正在搜尋雲端最新資料..."):
                df_history = fetch_data_with_buffer(conn)
                if not df_history.empty:
                    # 進行 Google Sheets 欄位標題防呆清洗
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
                            
                            # 檢查該紀錄是否已有 AI 衛教歷史文字，避免重複消耗 API 流量
                            existing_advice = latest_record.get(col_ai_record, "") if col_ai_record else ""
                            
                            if existing_advice and len(str(existing_advice)) > 50:
                                st.session_state.generated_advice = existing_advice
                                st.info("💡 已從雲端資料庫讀取現有衛教資訊（成功節省 Token 流量）。")
                            else:
                                # 若為空紀錄，則動態抓取該次受限結果並呼叫核心函式生成
                                muscle_info = latest_record.get('建議處理肌肉', '無資料')
                                clinical_context = f"判定: {latest_record.get('判定結果', '無')}, 肌肉: {muscle_info}"
                                
                                st.session_state.generated_advice = get_kpm_ai_advice(clinical_context, extra_note)
                                st.warning("🆕 雲端無舊文字紀錄，已為您產生新版 KPM 衛教。")
                            
                            st.success("✅ 雲端歷史處理完成")
                        else:
                            st.error("❌ 找不到該病歷號之歷史評估紀錄，請重新確認。")
                else:
                    st.error("❌ 雲端資料庫目前為空，無法進行檢索。")

    # 處理模式三：手動輸入自由分析（最適合大型篩檢、科技廠批量主訴輸入場景）
    else:
        manual_context = st.text_area(
            "請輸入臨床主訴或自由描述", 
            placeholder="例如：久坐科技廠工程師，主訴右邊高低肩，向前彎腰時大腿後側有嚴重硬緊拉扯感..."
        )
        if st.button("生成分析建議", key="btn_manual_generate"):
            with st.spinner("KPM-AI 正在讀取外部知識邊界，進行文字優化轉譯中..."):
                st.session_state.generated_advice = get_kpm_ai_advice(manual_context, extra_note)
            st.success("✅ 自由輸入分析完成！")

    # 顯示結果與無 Markdown 雜訊的極致白話純文字複製框（三大模式共用）
    if 'generated_advice' in st.session_state and st.session_state.generated_advice:
        st.markdown("---")
        st.subheader("📋 KPM AI 專家居家衛教單")
        st.info("💡 格式已通過視覺防呆優化，可直接全選複製貼入病人 LINE 訊息中，絕無亂碼。")
        
        # 採用您最滿意、最直覺的高彈性文字區塊，高度 500 像素，方便一鍵剪貼
        st.text_area(
            "📋 LINE / 記事本專用純文字（治療師可直接複製）", 
            value=st.session_state.generated_advice, 
            height=500
        )
        
        # 存回雲端之延伸接口預留
        if st.button("💾 將此衛教同步保存至該病患雲端欄位"):
            st.toast("提示：此功能需要配合您 st.connection 試算表的 Update 寫入權限，目前建議先複製使用。")

# 時區顯示 (依據 SOP 要求)
st.caption(f"系統時間：{datetime.now(tz_taiwan).strftime('%Y-%m-%d %H:%M:%S')} (Taipei)")
