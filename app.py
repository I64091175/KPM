import streamlit as st
import pandas as pd
import plotly.express as px

from config.settings import configure_gemini, get_gsheets_connection
from config.constants import (
    APP_TITLE,
    ACTIONS,
    SCORE_OPTIONS,
    IMAGE_MAPPING,
    ATLAS_GROUPS,
    IMAGE_DIR,
)
from config.styles import apply_custom_css
from utils.time_utils import get_today_taipei, format_display_time
from services.data_service import (
    fetch_main_assessment_data,
    filter_by_patient_id,
    safe_sort_by_datetime,
)
from services.archive_service import (
    fetch_latest_ai_advice,
    fetch_ai_history,
    save_ai_advice,
)
from services.ai_service import get_ai_advice

# =========================
# 基本設定與初始化
# =========================

st.set_page_config(page_title="KPM 筋膜評估系統", layout="centered")

apply_custom_css()
ai_enabled, ai_msg = configure_gemini()
conn = get_gsheets_connection()

st.title(APP_TITLE)


# =========================
# Session State 初始化
# =========================

def init_session_state():
    defaults = {
        "latest_results": [],
        "latest_summary_text": "",
        "latest_ai_text": "",
        "latest_ai_raw_text": "",
        "latest_ai_reasons": [],
        "last_patient_id": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


# =========================
# 簡化版規則映射（可跑版）
# 說明：
# 你原始檔中的完整規則資料庫片段未完整出現在上傳文字中，
# 所以這裡先用「動作觀察 → 初步線別關鍵字」的安全簡化版。
# 後續若你把完整規則庫補給我，我可以再幫你換成原始判定版。
# =========================

ACTION_HINTS = {
    "CF": {
        "label": "頸部前彎",
        "depth": "淺層",
        "keywords": ["淺背線", "側線"],
        "muscles": "頸後側、肩頸、上背軟組織張力需再確認",
    },
    "CE": {
        "label": "頸部後仰",
        "depth": "深層",
        "keywords": ["淺前線", "深前線"],
        "muscles": "頸前側、胸廓前側、深層穩定群需再確認",
    },
    "CRR": {
        "label": "頸部右旋",
        "depth": "淺層",
        "keywords": ["側線", "螺旋線"],
        "muscles": "右側頸部、上斜方與胸鎖乳突區域需再確認",
    },
    "CRL": {
        "label": "頸部左旋",
        "depth": "淺層",
        "keywords": ["側線", "螺旋線"],
        "muscles": "左側頸部、上斜方與胸鎖乳突區域需再確認",
    },
    "CR": {
        "label": "頸部側屈",
        "depth": "淺層",
        "keywords": ["側線"],
        "muscles": "頸側壁、提肩胛與肩頸外側張力需再確認",
    },
    "RAU": {
        "label": "右上肢上舉",
        "depth": "淺層",
        "keywords": ["前功能線", "後功能線", "淺前手臂線", "淺後手臂線"],
        "muscles": "右肩前後側、肩胛穩定與手臂線張力需再確認",
    },
    "RAD": {
        "label": "右上肢下壓/下放",
        "depth": "深層",
        "keywords": ["後功能線", "深前線", "深前手臂線"],
        "muscles": "右側肩胛控制、胸廓與深層穩定群需再確認",
    },
    "LAU": {
        "label": "左上肢上舉",
        "depth": "淺層",
        "keywords": ["前功能線", "後功能線", "淺前手臂線", "淺後手臂線"],
        "muscles": "左肩前後側、肩胛穩定與手臂線張力需再確認",
    },
    "LAD": {
        "label": "左上肢下壓/下放",
        "depth": "深層",
        "keywords": ["後功能線", "深前線", "深前手臂線"],
        "muscles": "左側肩胛控制、胸廓與深層穩定群需再確認",
    },
    "MSF": {
        "label": "多段前彎",
        "depth": "淺層",
        "keywords": ["淺背線", "螺旋線"],
        "muscles": "後側鏈、腿後側、下背及胸腰筋膜需再確認",
    },
    "MSE": {
        "label": "多段後仰",
        "depth": "深層",
        "keywords": ["淺前線", "深前線"],
        "muscles": "前側鏈、髖前側、腹部前壁與深層穩定群需再確認",
    },
    "MSRR": {
        "label": "多段右旋",
        "depth": "淺層",
        "keywords": ["螺旋線", "後功能線", "前功能線"],
        "muscles": "對角線旋轉鏈、軀幹旋轉與肩胛控制需再確認",
    },
    "MSRL": {
        "label": "多段左旋",
        "depth": "淺層",
        "keywords": ["螺旋線", "後功能線", "前功能線"],
        "muscles": "對角線旋轉鏈、軀幹旋轉與肩胛控制需再確認",
    },
    "MSSBR": {
        "label": "多段右側彎",
        "depth": "淺層",
        "keywords": ["側線"],
        "muscles": "右側腰、側腹、骨盆側穩定與臀中肌需再確認",
    },
    "MSSBL": {
        "label": "多段左側彎",
        "depth": "淺層",
        "keywords": ["側線"],
        "muscles": "左側腰、側腹、骨盆側穩定與臀中肌需再確認",
    },
    "CADS": {
        "label": "核心/深層穩定控制",
        "depth": "深層",
        "keywords": ["深前線"],
        "muscles": "核心深層、髖部深層與呼吸穩定控制需再確認",
    },
}

DEPTH_RANK = {"淺層": 0, "深層": 1, "最後處理": 2}


# =========================
# 輔助函式
# =========================

def is_restricted(score):
    return score in ["DS", "DA"]


def find_existing_column(df, candidates):
    if df is None or df.empty:
        return None

    for col in candidates:
        if col in df.columns:
            return col
    return None


def build_simple_results(user_scores, user_action_notes, user_priorities):
    """
    簡化版結果整合器：
    只要動作是 DS / DA，就整理成可顯示與可餵 AI 的結果。
    """
    results = []

    for act in ACTIONS:
        score = user_scores.get(act)
        if not is_restricted(score):
            continue

        hint = ACTION_HINTS.get(
            act,
            {
                "label": act,
                "depth": "深層",
                "keywords": [],
                "muscles": "請依臨床判斷補充",
            },
        )

        note = user_action_notes.get(act, "").strip()
        is_prio = user_priorities.get(act, False)

        image_list = []
        for keyword in hint["keywords"]:
            if keyword in IMAGE_MAPPING:
                image_list.append(IMAGE_MAPPING[keyword])

        result_item = {
            "action": act,
            "label": hint["label"],
            "score": score,
            "depth": hint["depth"],
            "keywords": hint["keywords"],
            "muscles": hint["muscles"],
            "note": note,
            "is_prio": is_prio,
            "images": list(dict.fromkeys(image_list)),
        }

        results.append(result_item)

    # 排序：先加權，再淺深層
    results = sorted(
        results,
        key=lambda x: (
            0 if x["is_prio"] else 1,
            DEPTH_RANK.get(x["depth"], 9),
            x["action"],
        ),
    )

    return results


def build_target_keywords(results):
    """
    給 AI 抽知識庫用的關鍵字
    """
    keywords = []
    for item in results:
        for k in item.get("keywords", []):
            keywords.append(k)

    return list(dict.fromkeys(keywords))


def build_clinical_summary(
    p_name,
    p_id,
    p_date,
    vas_score,
    p_assessor,
    p_note,
    results,
):
    """
    產出 AI 用的臨床摘要
    注意：
    這裡故意不放姓名與完整病歷號進 AI 內容，只保留去識別化資訊。
    """
    if not results:
        return (
            f"本次評估日期：{p_date}；VAS：{vas_score} 分。"
            f"目前未標記明確 DS/DA 受限項目。"
            f"臨床補充：{p_note if p_note else '無'}。"
        )

    priority_items = [r for r in results if r["is_prio"]]
    restricted_items = [
        f"{r['action']}（{r['label']}，{r['score']}）" for r in results[:8]
    ]

    priority_text = (
        "；".join([f"{r['action']}（{r['label']}）" for r in priority_items])
        if priority_items
        else "無"
    )

    summary = (
        f"本次評估日期：{p_date}；VAS：{vas_score} 分。"
        f"受限動作摘要：{'；'.join(restricted_items)}。"
        f"加權重點：{priority_text}。"
        f"評估人：{p_assessor if p_assessor else '未填寫'}。"
        f"臨床補充：{p_note if p_note else '無'}。"
    )

    return summary


def render_result_card(item):
    title_prefix = "🌟" if item["is_prio"] else ("🌿" if item["depth"] == "淺層" else "💎")

    st.markdown(
        f"""
<div class="{ 'priority-box' if item['is_prio'] else ('superficial-box' if item['depth']=='淺層' else 'deep-box') }">
{title_prefix} <b>{item['action']}｜{item['label']}</b><br>
分級：{item['score']}<br>
層級：{item['depth']}<br>
建議觀察重點：{item['muscles']}
</div>
""",
        unsafe_allow_html=True,
    )

    if item["note"]:
        st.caption(f"備註：{item['note']}")

    if item["keywords"]:
        st.caption(f"關聯線別關鍵字：{'、'.join(item['keywords'])}")

    if item["images"]:
        with st.expander("🔍 檢視對應圖譜"):
            for img in item["images"]:
                st.image(f"{IMAGE_DIR}/{img}", width=350)


def render_results(results):
    if not results:
        st.info("目前沒有 DS / DA 受限項目，請先到「主動快篩」標記分級。")
        return

    for item in results:
        render_result_card(item)


def render_trend_chart(df, title, x_col, y_col):
    if df is None or df.empty:
        return

    fig = px.line(
        df,
        x=x_col,
        y=y_col,
        title=title,
        markers=True,
    )
    st.plotly_chart(fig, use_container_width=True)


# =========================
# 建立頁籤
# =========================

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "📋 基本資料",
        "🦴 主動快篩",
        "📊 判定結果",
        "📚 完整圖譜",
        "📈 趨勢追蹤",
        "🤖 AI 助手",
    ]
)


# =========================
# Tab 1：基本資料
# =========================

with tab1:
    st.subheader("👤 基本資料")

    p_name = st.text_input("病人姓名", key="p_name")
    p_id = st.text_input("病歷號", key="p_id")
    p_date = st.date_input("評估日期", value=get_today_taipei(), key="p_date")
    vas_score = st.slider("🤒 病人自覺整體分數（10分最痛）", 0, 10, 5, key="vas_score")
    p_assessor = st.text_input("評估人", key="p_assessor")
    p_note = st.text_area("整體臨床總結備註", key="p_note")

    st.session_state["last_patient_id"] = p_id.strip()


# =========================
# Tab 2：主動快篩
# =========================

with tab2:
    st.subheader("🦴 主動快篩")
    st.info("請標註評估等級。若為本次核心問題，請打勾「⭐ 加權」。")

    user_scores = {}
    user_action_notes = {}
    user_priorities = {}

    for i, act in enumerate(ACTIONS, 1):
        hint = ACTION_HINTS.get(act, {})
        action_label = hint.get("label", act)

        st.markdown(
            f"<div class='action-title'>{i}. 動作：{act} ｜ {action_label}</div>",
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns([3, 1])

        user_scores[act] = c1.segmented_control(
            label=act,
            options=SCORE_OPTIONS,
            key=f"score_{act}",
            selection_mode="single",
            label_visibility="collapsed",
        )

        user_priorities[act] = c2.checkbox("⭐ 加權", key=f"prio_{act}")

        user_action_notes[act] = st.text_input(
            f"備註（{act}）",
            key=f"note_{act}",
        )

        st.divider()

    # 存到 session，供 tab3 / tab6 使用
    current_results = build_simple_results(user_scores, user_action_notes, user_priorities)

    st.session_state["latest_results"] = current_results
    st.session_state["latest_summary_text"] = build_clinical_summary(
        p_name=p_name,
        p_id=p_id,
        p_date=p_date,
        vas_score=vas_score,
        p_assessor=p_assessor,
        p_note=p_note,
        results=current_results,
    )


# =========================
# Tab 3：判定結果
# =========================

with tab3:
    st.subheader("📊 判定結果（簡化版整合）")

    results = st.session_state.get("latest_results", [])

    if st.button("🔄 重新整理判定結果", key="refresh_results"):
        results = build_simple_results(user_scores, user_action_notes, user_priorities)
        st.session_state["latest_results"] = results
        st.session_state["latest_summary_text"] = build_clinical_summary(
            p_name=p_name,
            p_id=p_id,
            p_date=p_date,
            vas_score=vas_score,
            p_assessor=p_assessor,
            p_note=p_note,
            results=results,
        )

    render_results(results)

    if results:
        with st.expander("📄 檢視本次臨床摘要（AI 將使用這份摘要）"):
            st.write(st.session_state.get("latest_summary_text", ""))


# =========================
# Tab 4：完整圖譜
# =========================

with tab4:
    st.subheader("📚 完整圖譜")

    for title, imgs in ATLAS_GROUPS.items():
        with st.expander(f"📍 {title}"):
            for img in imgs:
                st.image(f"{IMAGE_DIR}/{img}", use_container_width=True)


# =========================
# Tab 5：趨勢追蹤
# =========================

with tab5:
    st.subheader("📈 趨勢追蹤")

    search_id = st.text_input("🔍 輸入病歷號查詢歷史紀錄", key="q_id_v145")

    if search_id.strip():
        df_main = fetch_main_assessment_data(conn, ttl=10)

        if df_main is None or df_main.empty:
            st.info("目前主資料表沒有可讀取的資料，或 Google Sheets 連線尚未完成。")
        else:
            pid_col = find_existing_column(df_main, ["病歷號", "patient_id", "PID", "p_id"])
            date_col = find_existing_column(df_main, ["日期", "評估日期", "date", "Date"])
            vas_col = find_existing_column(df_main, ["VAS", "vas", "疼痛分數", "痛覺分數"])

            if pid_col is None:
                st.warning("主資料表找不到『病歷號』欄位，無法做歷史查詢。")
            else:
                filtered_df = filter_by_patient_id(df_main, search_id, patient_id_column=pid_col)
                filtered_df = safe_sort_by_datetime(filtered_df, datetime_column=date_col if date_col else "日期")

                if filtered_df.empty:
                    st.info("查無此病歷號的主表歷史紀錄。")
                else:
                    st.success(f"找到 {len(filtered_df)} 筆主表資料。")
                    st.dataframe(filtered_df, use_container_width=True)

                    if date_col and vas_col:
                        try:
                            plot_df = filtered_df.copy()
                            plot_df[date_col] = pd.to_datetime(plot_df[date_col], errors="coerce")
                            plot_df[vas_col] = pd.to_numeric(plot_df[vas_col], errors="coerce")
                            plot_df = plot_df.dropna(subset=[date_col, vas_col])

                            if not plot_df.empty:
                                render_trend_chart(plot_df, "VAS 趨勢", date_col, vas_col)
                        except Exception as e:
                            st.warning(f"VAS 圖表產生失敗：{str(e)}")

        st.markdown("---")
        st.subheader("🤖 AI 衛教歷史")

        ai_history_df = fetch_ai_history(conn, search_id)

        if ai_history_df is None or ai_history_df.empty:
            st.info("查無此病歷號的 AI 衛教歷史。")
        else:
            st.dataframe(ai_history_df, use_container_width=True)


# =========================
# Tab 6：AI 助手
# =========================

with tab6:
    st.header("🤖 AI 臨床衛教助手")

    if ai_enabled:
        st.success("✅ AI 功能已啟用")
    else:
        st.warning(f"⚠️ AI 功能目前未啟用：{ai_msg}")

    st.caption(f"系統時間：{format_display_time()} (Taipei)")

    target_pid = st.session_state.get("last_patient_id", "").strip()

    ai_mode = st.radio(
        "功能選擇",
        [
            "⚡ 根據當前評估一鍵生成",
            "🔍 抓取歷史評估結果",
            "✍️ 手動輸入狀況分析",
        ],
        key="ai_mode",
    )

    results = st.session_state.get("latest_results", [])
    summary_text = st.session_state.get("latest_summary_text", "")

    if ai_mode == "⚡ 根據當前評估一鍵生成":
        st.write("系統將使用目前 Tab1 + Tab2 的資料產生衛教內容。")

        if not target_pid:
            st.info("尚未輸入病歷號，仍可生成 AI 文字，但無法寫入歷史 archive。")

        if not results:
            st.warning("目前沒有可用的判定結果，請先到「主動快篩」完成標記。")

        if st.button("🚀 一鍵生成 AI 衛教", key="btn_ai_generate_current"):
            if not results:
                st.error("沒有 DS/DA 受限項目，無法進行本次 AI 生成。")
            else:
                target_keywords = build_target_keywords(results)

                with st.spinner("AI 正在生成衛教內容中..."):
                    ai_response = get_ai_advice(
                        clinical_summary=summary_text,
                        extra_info=p_note if p_note else "",
                        target_keywords=target_keywords,
                    )

                st.session_state["latest_ai_text"] = ai_response.get("text", "")
                st.session_state["latest_ai_raw_text"] = ai_response.get("raw_text", "")
                st.session_state["latest_ai_reasons"] = ai_response.get("reasons", [])

                if ai_response.get("success", False):
                    st.success("✅ AI 衛教內容生成完成。")
                else:
                    st.warning("AI 目前處於降級模式，已回傳安全備援內容。")

    elif ai_mode == "🔍 抓取歷史評估結果":
        st.write("從雲端 archive 抓取該病人最新的 AI 衛教紀錄。")

        history_pid = st.text_input(
            "請輸入病歷號",
            value=target_pid,
            key="history_ai_pid",
        )

        if st.button("📥 抓取最新 AI 衛教", key="btn_ai_fetch_history"):
            latest_record = fetch_latest_ai_advice(conn, history_pid)

            if not latest_record:
                st.warning("查無此病歷號的 AI 歷史紀錄。")
            else:
                st.session_state["latest_ai_text"] = latest_record.get("AI衛教建議", "")
                st.session_state["latest_summary_text"] = latest_record.get("判定結果", "")
                st.success("✅ 已載入最新 AI 衛教紀錄。")

    elif ai_mode == "✍️ 手動輸入狀況分析":
        st.write("適合沒有進行完整快篩，但想先做文字衛教初稿時使用。")

        manual_text = st.text_area(
            "請輸入病人目前狀況（請避免輸入姓名與完整病歷號）",
            height=180,
            key="manual_ai_input",
        )

        manual_keywords = st.multiselect(
            "可手動指定關聯線別（提高知識庫命中率）",
            options=[
                "淺背線",
                "淺前線",
                "側線",
                "螺旋線",
                "深前線",
                "前功能線",
                "後功能線",
                "淺前手臂線",
                "淺後手臂線",
                "深前手臂線",
                "深後手臂線",
            ],
            key="manual_ai_keywords",
        )

        if st.button("📝 產生手動 AI 衛教", key="btn_ai_generate_manual"):
            if not manual_text.strip():
                st.error("請先輸入手動描述內容。")
            else:
                with st.spinner("AI 正在分析手動輸入內容..."):
                    ai_response = get_ai_advice(
                        clinical_summary=manual_text.strip(),
                        extra_info="",
                        target_keywords=manual_keywords,
                    )

                st.session_state["latest_ai_text"] = ai_response.get("text", "")
                st.session_state["latest_ai_raw_text"] = ai_response.get("raw_text", "")
                st.session_state["latest_ai_reasons"] = ai_response.get("reasons", [])

                if ai_response.get("success", False):
                    st.success("✅ AI 衛教內容生成完成。")
                else:
                    st.warning("AI 目前處於降級模式，已回傳安全備援內容。")

    st.markdown("---")
    st.subheader("🧾 AI 輸出結果")

    latest_ai_text = st.session_state.get("latest_ai_text", "")
    latest_ai_reasons = st.session_state.get("latest_ai_reasons", [])

    if latest_ai_text:
        st.text_area(
            "可直接複製給病人的文字",
            value=latest_ai_text,
            height=420,
            key="output_ai_text",
        )

        if latest_ai_reasons:
            with st.expander("⚠️ AI 格式提醒 / 修正資訊"):
                for reason in latest_ai_reasons:
                    st.write(f"• {reason}")

        if target_pid.strip():
            if st.button("💾 儲存本次 AI 衛教到雲端", key="btn_save_ai_archive"):
                save_ai_advice(
                    conn=conn,
                    patient_id=target_pid,
                    ai_text=latest_ai_text,
                    summary_text=st.session_state.get("latest_summary_text", ""),
                )
    else:
        st.info("尚未生成 AI 內容。")

