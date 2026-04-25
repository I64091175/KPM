import streamlit as st
from datetime import date, datetime, timedelta, timezone
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.express as px

# ==========================================
# APP NAME: KPM 關鍵點評估系統
# VERSION: 1.2 (歷史功能優化版)
# BASE: V1.2 正式修復版 (保留 1-4 頁)
# UPDATE: 2026-04-25
# ==========================================

# 1. 基礎設定 (Tab 1-4 核心邏輯保持不變)
st.set_page_config(page_title="KPM 筋膜評估系統 V1.2", layout="centered")
tz_taiwan = timezone(timedelta(hours=8))

def fetch_data_no_cache(_conn):
    try:
        return _conn.read(worksheet="Sheet1", ttl=0)
    except Exception as e:
        if "429" in str(e):
            st.error("⚠️ 系統連線繁忙，請等候約 60 秒後重新整理網頁。")
        return pd.DataFrame()

conn = st.connection("gsheets", type=GSheetsConnection)

# CSS 樣式 (保留 V1.1/V1.2 原有樣式)
st.markdown("""
    <style>
    .action-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 5px; color: #1E88E5; }
    .superficial-header { color: #2E7D32; font-weight: bold; border-left: 5px solid #2E7D32; padding-left: 10px; margin-top: 20px; }
    .superficial-box { border: 2px solid #2E7D32; padding: 15px; border-radius: 8px; background-color: #F1F8E9; margin-bottom: 10px; color: #1B5E20; }
    .deep-box { background-color: #FFF3E0; border-left: 5px solid #EF6C00; padding: 15px; border-radius: 8px; color: #BF360C; margin-bottom: 10px; }
    .priority-box { background-color: #F3E5F5; border: 2px solid #7B1FA2; padding: 15px; border-radius: 8px; color: #4A148C; margin-bottom: 15px; font-weight: bold; }
    .muscle-text { font-weight: bold; color: #D84315; margin-top: 5px; }
    .ankle-box { background-color: #E3F2FD; padding: 15px; border-radius: 8px; border: 2px solid #1E88E5; color: #000000; margin-top: 20px; font-weight: bold; }
    /* 新增：末次評估提示框樣式 */
    .last-record-box { background-color: #E8F5E9; border: 2px solid #2E7D32; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🩺 KPM 關鍵點評估系統 V1.2")

# --- 2. 核心資料定義與判定邏輯 (Tab 1-4 使用) ---
ACTIONS = ["CF", "CE", "CRR", "CRL", "CR", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS"]
SCORE_MAP = {"DA": 1, "DS": 2, "FS": 3, "FA": 4}
COLOR_MAP = {"DA": "#EF553B", "DS": "#FFA15A", "FS": "#636EFA", "FA": "#00CC96"}

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

# --- 3. 介面分頁 (1-4 頁代碼完全保留) ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 病人資訊", "📝 快速評估", "📊 判定結果", "📚 筋膜圖譜", "📈 歷史追蹤"])

with tab1:
    st.subheader("👤 病人基本資料")
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
    st.subheader("📊 判定結果摘要")
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
            item = {**rule, "is_prio": not rule["pair"].isdisjoint(set(priority_list))}
            if item["is_prio"]: weighted_res.append(item)
            elif s1 == "DA": da_da_res.append(item)
            else: ds_ds_res.append(item)

    def display_results(res_list, title):
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
                    with st.expander(f"🔍 檢視圖譜: {res['result']}"):
                        for img in imgs: st.image(f"images/{img}", width=350)

    display_results(weighted_res, "⭐ 加權重點對應")
    display_results(da_da_res, "🟦 DA-DA 對應結果")
    display_results(ds_ds_res, "🟧 DS-DS 對應結果")

    all_pairs = [" + ".join(sorted(list(r["pair"]))) for r in weighted_res + da_da_res + ds_ds_res]
    for p_str in ["MSRR + MSSBL", "MSRL + MSSBR"]:
        if p_str in all_pairs:
            st.markdown(f"<div class='ankle-box'>🔍 偵測到 {p_str} 相對應，請加測：</div>", unsafe_allow_html=True)
            side = "右" if "MSRR" in p_str else "左"
            opp = "左" if side == "右" else "右"
            if st.checkbox(f"{side}踝內翻受限 (處理{side}側線)", key=f"ak1_{p_str}"): st.info(f"💡 建議處理：{side}側線 (淺層)")
            if st.checkbox(f"{opp}踝外翻受限 (處理{opp}深前線)", key=f"ak2_{p_str}"): st.info(f"💡 建議處理：{opp}深前線 (深層)")

    st.divider()
    if st.button("🚀 完成評估並同步雲端"):
        if not p_name or not p_id:
            st.error("請輸入姓名與病歷號！")
        else:
            try:
                act_notes = [f"{a}:{user_action_notes[a].strip()}" for a in ACTIONS if user_action_notes[a].strip()]
                prio_tags = [f"{a}(⭐)" for a in priority_list]
                combined_details = "/".join(act_notes + prio_tags)
                final_note = f"{p_note} | 詳細: {combined_details}" if p_note and combined_details else (p_note or combined_details)
                now_tw = datetime.now(tz_taiwan)
                final_dt_str = now_tw.strftime("%Y-%m-%d %H:%M") if p_date >= now_tw.date() else f"{p_date} (補)"
                record = {"日期": final_dt_str, "評估人": p_assessor, "病人姓名": p_name, "病歷號": f"'{p_id}", "病人自覺分數": vas_score, "加權關鍵點": ", ".join(priority_list), "判定結果": " / ".join([res['result'] for res in weighted_res + da_da_res + ds_ds_res]), "備註": final_note}
                record.update(user_scores)
                df_old = fetch_data_no_cache(conn)
                df_final = pd.concat([df_old, pd.DataFrame([record])], ignore_index=True)
                conn.update(worksheet="Sheet1", data=df_final)
                st.success(f"✅ 資料已同步至 Google Sheets！時間：{final_dt_str}"); st.balloons()
            except Exception as e:
                st.error(f"同步失敗: {e}")

with tab4:
    st.subheader("📚 完整解剖圖譜")
    atlas = {"FF 功能線": ["FF1.jpg", "FF2.jpg"], "SBL 淺背線": ["SBL.jpg"], "SFL 淺前線": ["SFL.jpg"], "LL 側線": ["LL.jpg"], "SPL 螺旋線": ["SPL.jpg"], "DFL 深前線": ["DFL.jpg"], "手臂線系列": ["SFAL.jpg", "SBAL.jpg", "DFAL.jpg", "DBAL.jpg"]}
    for title, imgs in atlas.items():
        with st.expander(f"📍 {title}"):
            for img in imgs: st.image(f"images/{img}", use_container_width=True)

# --- 4. 修改後之 Tab 5 歷史功能 (僅針對此部分進行更動) ---
with tab5:
    st.subheader("📈 歷史恢復趨勢分析")
    search_id = st.text_input("🔍 輸入病歷號查詢歷史紀錄", key="q_id_v12")
    
    if search_id:
        all_df = fetch_data_no_cache(conn)
        
        if not all_df.empty:
            # 格式清洗與篩選
            all_df['病歷號'] = all_df['病歷號'].astype(str).str.lstrip("'").str.strip()
            p_history = all_df[all_df["病歷號"] == str(search_id).strip()].copy()
            
            if not p_history.empty:
                # 排序資料，確保獲取最新評估
                p_history['sort_dt'] = pd.to_datetime(p_history['日期'].str.replace(" (補)", ""), errors='coerce')
                p_history = p_history.sort_values("sort_dt")
                
                # --- 新增功能：顯示末次評估 DA/DS 狀況 ---
                last_record = p_history.iloc[-1]  # 獲取最後一筆紀錄
                
                st.markdown("### 📋 該病患末次評估核心狀況")
                st.markdown(f"""
                    <div class="last-record-box">
                        <b>🕙 最近評估時間：</b> {last_record['日期']}<br>
                        <b>🛑 上次判定結果 (DA/DS)：</b><br>
                        <span style='color: #D84315; font-size: 1.1rem;'>{last_record['判定結果']}</span><br><br>
                        <b>📝 上次治療備註：</b><br>
                        {last_record['備註']}
                    </div>
                """, unsafe_allow_html=True)
                
                # 保留長條圖：自覺分數變化
                st.markdown("### 🤒 自覺分數趨勢")
                recent = p_history.tail(6) # 顯示最近 6 次趨勢
                fig_bar = px.bar(recent, x="日期", y="病人自覺分數", 
                                 color_discrete_sequence=["#1E88E5"], 
                                 text_auto=True, 
                                 title="病患疼痛自覺量表 (VAS) 演變")
                st.plotly_chart(fig_bar, use_container_width=True)

                # 列表顯示完整歷史
                with st.expander("📂 展開完整歷史明細"):
                    st.dataframe(p_history.sort_values("sort_dt", ascending=False)[["日期", "判定結果", "病人自覺分數", "備註"]])
                
            else:
                # 找不到該病歷號之顯示
                st.error("找不到此病歷號")
        else:
            st.warning("資料庫目前為空，請先上傳資料。")
