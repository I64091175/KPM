# ==========================================
# APP NAME: KPM 關鍵點評估系統
# VERSION: 1.01 (時區與圖表修正版)
# BASE: V1.0 穩定地基
# UPDATE: 2026-04-05
# FIX: 
#   1. 修正台灣時區判定，解決 00:00 後自動變 (補) 的問題
#   2. 修正直方圖 X 軸格式，確保 (補) 資料正常顯示
# VERSION: 1.1 (臨床決策加權版)
# BASE: V1.01 穩定地基
# UPDATE: 2026-04-08
# FEATURES: 
#   - CR 動作調整至第 5 位
#   - 新增 VAS 病人自覺分數滑桿 (0-10)
#   - 新增 ⭐ 關鍵點加權功能 (一鍵置頂重點)
#   - 自動修正時區 (UTC+8) 與 歷史圖表 (補) 字樣顯示
#   - 流量 429 報錯隱藏與中文友善提示
# ==========================================

import streamlit as st
@@ -15,20 +18,23 @@
import plotly.graph_objects as go
import plotly.express as px

# 1. 基礎設定與台灣時區 (UTC+8)
st.set_page_config(page_title="KPM 筋膜評估系統", layout="centered")
# 1. 基礎設定與時區
st.set_page_config(page_title="KPM 筋膜評估系統 V1.1", layout="centered")
tz_taiwan = timezone(timedelta(hours=8))

def fetch_data_no_cache(_conn):
try:
return _conn.read(worksheet="Sheet1", ttl=0)
except Exception as e:
        st.error(f"讀取資料庫失敗: {e}")
        if "429" in str(e):
            st.error("⚠️ 系統連線繁忙，請等候約 60 秒後重新整理網頁。")
        else:
            st.error(f"讀取資料庫失敗: {e}")
return pd.DataFrame()

conn = st.connection("gsheets", type=GSheetsConnection)

# CSS 樣式
# CSS 樣式：包含加權置頂的視覺效果
st.markdown("""
   <style>
   .stHeader { font-size: 1.2rem !important; color: #2c3e50; }
@@ -40,16 +46,27 @@ def fetch_data_no_cache(_conn):
       padding: 15px;
       border-radius: 8px;
       color: #BF360C;
        margin-bottom: 10px;
    }
    /* 加權重點處理樣式 */
    .priority-box {
        background-color: #F3E5F5;
        border: 2px solid #7B1FA2;
        padding: 15px;
        border-radius: 8px;
        color: #4A148C;
       margin-bottom: 15px;
        font-weight: bold;
   }
   hr { margin-top: 1rem; margin-bottom: 1rem; border-bottom: 2px solid #eee; }
   </style>
   """, unsafe_allow_html=True)

st.title("🩺 KPM 關鍵點評估系統")
st.title("🩺 KPM 關鍵點評估系統 V1.1")

# --- 2. 核心資料定義 ---
ACTIONS = ["CF", "CE", "CRR", "CRL", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS", "CR"]
# CR 調整至第 5 位
ACTIONS = ["CF", "CE", "CRR", "CRL", "CR", "RAU", "RAD", "LAU", "LAD", "MSF", "MSE", "MSRR", "MSRL", "MSSBR", "MSSBL", "CADS"]
SCORE_MAP = {"DA": 1, "DS": 2, "FS": 3, "FA": 4}
COLOR_MAP = {"DA": "#EF553B", "DS": "#FFA15A", "FS": "#636EFA", "FA": "#00CC96"}

@@ -90,42 +107,75 @@ def fetch_data_no_cache(_conn):
st.subheader("👤 病人基本資料")
p_name = st.text_input("病人姓名", key="p_name")
p_id = st.text_input("病歷號/身分證號", key="p_id", placeholder="例如: 00123")
    today_taiwan = datetime.now(tz_taiwan).date() # 強制同步台灣日期
    today_taiwan = datetime.now(tz_taiwan).date()
p_date = st.date_input("評估日期", value=today_taiwan)
    
    # 新增 VAS 分數滑桿
    vas_score = st.slider("🤒 病人自覺整體分數 (10分最痛 / 0分不痛)", 0, 10, 5)
    
p_assessor = st.text_input("評估人", key="p_assessor")
p_note = st.text_area("整體臨床總結備註", height=100)

with tab2:
    st.info("完成評估後，請切換至第三頁查看結果")
    st.info("請標註評估等級。若該動作為核心受限，請點選 ⭐ 加權。")
user_scores = {}
user_action_notes = {}
    user_priorities = {}
    
for i, act in enumerate(ACTIONS, 1):
st.markdown(f"<div class='action-title'>{i}. 動作: {act}</div>", unsafe_allow_html=True)
        user_scores[act] = st.segmented_control(label=act, options=["FA", "FS", "DS", "DA"], key=f"s_{act}", selection_mode="single", label_visibility="collapsed")
        col_eval, col_prio = st.columns([3, 1])
        with col_eval:
            user_scores[act] = st.segmented_control(label=act, options=["FA", "FS", "DS", "DA"], key=f"s_{act}", selection_mode="single", label_visibility="collapsed")
        with col_prio:
            user_priorities[act] = st.checkbox("⭐ 加權", key=f"prio_{act}")
        
user_action_notes[act] = st.text_input(f"備註 ({act})", key=f"note_{act}")
st.divider()

with tab3:
st.subheader("📊 判定結果摘要")
da_list = [k for k, v in user_scores.items() if v == "DA"]
ds_list = [k for k, v in user_scores.items() if v == "DS"]
    
    # 總結清單回歸
    priority_list = [k for k, v in user_priorities.items() if v]

    # 1. 頂端摘要
if da_list or ds_list:
st.write(f"🛑 **DA 項目:** {', '.join(da_list) if da_list else '無'}")
st.write(f"⚠️ **DS 項目:** {', '.join(ds_list) if ds_list else '無'}")
        if priority_list:
            st.write(f"🌟 **關鍵加權點:** {', '.join(priority_list)}")
st.divider()

    matches = []
    # 2. 判定邏輯
    matched_results = []
    source_list = da_list if da_list else ds_list
    
for rule in TREATMENT_DATABASE:
        if rule["pair"].issubset(set(da_list)): matches.append(rule)
    if not matches:
        for rule in TREATMENT_DATABASE:
            if rule["pair"].issubset(set(ds_list)): matches.append(rule)

    if matches:
        for m in matches:
            if m["pair"] in DEEP_PAIRS:
        if rule["pair"].issubset(set(source_list)):
            # 檢查組合內是否有動作被加權
            is_prio = not rule["pair"].isdisjoint(set(priority_list))
            matched_results.append({"rule": rule, "is_prio": is_prio})

    # 3. 排序：加權項目置頂
    matched_results = sorted(matched_results, key=lambda x: x["is_prio"], reverse=True)

    if matched_results:
        for item in matched_results:
            m = item["rule"]
            is_prio = item["is_prio"]
            is_deep = m["pair"] in DEEP_PAIRS
            
            # 加權視覺處理
            if is_prio:
                st.markdown(f"""
                    <div class="priority-box">
                        🔥 重點處理項目<br>
                        動作組合: {' + '.join(sorted(list(m['pair'])))}<br><br>
                        結果: {m['result']}
                    </div>
                """, unsafe_allow_html=True)
            elif is_deep:
st.markdown(f"""
                   <div class="deep-box">
                       <strong>💎 深層判定</strong><br>
@@ -137,43 +187,52 @@ def fetch_data_no_cache(_conn):
st.markdown("<div class='superficial-header'>🌿 淺層判定</div>", unsafe_allow_html=True)
st.success(f"**{' + '.join(sorted(list(m['pair'])))}** \n\n {m['result']}")

            # 圖片顯示
imgs = [v for k, v in IMAGE_MAPPING.items() if k in m['result']]
if imgs:
                with st.expander("🔍 檢視對應筋膜圖 (50%)"):
                with st.expander("🔍 檢視圖譜 (50%)"):
for img in imgs:
l, mid, r = st.columns([1, 2, 1])
try: mid.image(f"images/{img}", use_container_width=True)
                        except: mid.error(f"找不到圖片: images/{img}")
                        except: mid.error(f"找不到圖片: {img}")
else:
        st.info("目前組合尚未觸發判定。")
        st.info("目前點選組合尚未觸發判定。")

st.divider()
if st.button("🚀 完成評估並同步雲端"):
if not p_name or not p_id:
st.error("請輸入姓名與病歷號！")
else:
try:
                # 1. 備註合併
                # 備註合併邏輯
act_notes = [f"{a}:{user_action_notes[a].strip()}" for a in ACTIONS if user_action_notes[a].strip()]
                combined_details = "/".join(act_notes)
                # 若有加權，也在細節中標註
                prio_tags = [f"{a}(⭐)" for a in priority_list]
                combined_details = "/".join(act_notes + prio_tags)
final_note = f"{p_note} | 詳細: {combined_details}" if p_note and combined_details else (p_note or combined_details)

                # 2. 自動時間邏輯 (修正時區判定)
                # 時間邏輯
now_tw = datetime.now(tz_taiwan)
                if p_date >= now_tw.date():
                    final_dt_str = now_tw.strftime("%Y-%m-%d %H:%M")
                else:
                    final_dt_str = f"{p_date} (補)"
                final_dt_str = now_tw.strftime("%Y-%m-%d %H:%M") if p_date >= now_tw.date() else f"{p_date} (補)"

                # 3. 同步
                record = {"日期": final_dt_str, "評估人": p_assessor, "病人姓名": p_name, "病歷號": f"'{p_id}", "判定結果": " / ".join([m['result'] for m in matches]), "備註": final_note}
                # 同步資料
                record = {
                    "日期": final_dt_str, "評估人": p_assessor, "病人姓名": p_name, "病歷號": f"'{p_id}",
                    "病人自覺分數": vas_score, "加權關鍵點": ", ".join(priority_list),
                    "判定結果": " / ".join([res['rule']['result'] for res in matched_results]), 
                    "備註": final_note
                }
record.update(user_scores)
                
df_old = fetch_data_no_cache(conn)
df_final = pd.concat([df_old, pd.DataFrame([record])], ignore_index=True)
conn.update(worksheet="Sheet1", data=df_final)
                st.success(f"✅ 資料已同步！({final_dt_str})"); st.balloons()
                st.success(f"✅ 資料已同步！時間：{final_dt_str}"); st.balloons()
except Exception as e:
                st.error(f"同步失敗: {e}")
                if "429" in str(e):
                    st.error("⚠️ 雲端連線過於繁忙，請等待約 60 秒後再試一次。")
                else:
                    st.error(f"同步失敗: {e}")

with tab4:
st.subheader("📚 完整筋膜解剖圖譜")
@@ -193,13 +252,14 @@ def fetch_data_no_cache(_conn):
all_df['病歷號'] = all_df['病歷號'].astype(str).str.lstrip("'").str.strip()
p_history = all_df[all_df["病歷號"] == str(search_id).strip()].copy()
if not p_history.empty:
                    # 排序修正
p_history['sort_dt'] = pd.to_datetime(p_history['日期'].str.replace(" (補)", "", regex=False), errors='coerce')
p_history = p_history.sort_values("sort_dt")

st.success(f"找到 {len(p_history)} 筆紀錄。")
recent = p_history.tail(4)

                    # 統計圖：修正 X 軸格式
                    # 統計圖
stats_list = []
for _, row in recent.iterrows():
counts = {"DA": 0, "DS": 0, "FS": 0, "FA": 0}
@@ -209,8 +269,7 @@ def fetch_data_no_cache(_conn):
for lvl, cnt in counts.items(): stats_list.append({"日期": row["日期"], "等級": lvl, "次數": cnt})

fig_bar = px.bar(pd.DataFrame(stats_list), x="日期", y="次數", color="等級", color_discrete_map=COLOR_MAP, category_orders={"等級": ["DA", "DS", "FS", "FA"]}, text_auto=True)
                    # ✅ 核心修正：強制將 X 軸視為文字，防止 (補) 消失
                    fig_bar.update_layout(xaxis_type='category')
                    fig_bar.update_layout(xaxis_type='category') # 核心：確保 (補) 出現
st.plotly_chart(fig_bar, use_container_width=True)

# 雷達圖
@@ -221,5 +280,4 @@ def fetch_data_no_cache(_conn):
fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 4], tickvals=[1,2,3,4], ticktext=['DA','DS','FS','FA'])))
st.plotly_chart(fig_radar, use_container_width=True)

                    p_display = p_history.sort_values("sort_dt", ascending=False)
                    st.dataframe(p_display[["日期", "判定結果", "備註"]])
                    st.dataframe(p_history.sort_values("sort_dt", ascending=False)[["日期", "判定結果", "備註"]])
