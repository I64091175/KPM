#這個檔案負責：
# Gemini prompt 建立、去識別化、fallback 模型輪詢、格式檢查、後處理。
# 目前主程式裡 get_kpm_ai_advice() 
#  SOP 明確要求：只能用知識庫內容、不能自行編造、不能輸出 Markdown、不能帶內部線名，最後要固定警語
# services/ai_service.py

import re
import streamlit as st
import google.generativeai as genai

from config.constants import FALLBACK_MODELS
from config.settings import is_ai_enabled
from services.kb_service import load_all_ai_context, extract_kb_sections


FINAL_WARNING = "以上建議僅供參考，請由專業物理治療師現場指導。"

# 內部筋膜線代號 -> 白話名稱
INTERNAL_TERM_REPLACEMENTS = {
    "SBL": "背部後側筋膜線",
    "SFL": "身體前側筋膜線",
    "LL": "身體側邊筋膜線",
    "DFL": "深層前側穩定筋膜線",
    "DFAL": "前臂深層前側筋膜線",
    "DBAL": "前臂深層後側筋膜線",
    "SFAL": "前臂前側筋膜線",
    "SBAL": "前臂後側筋膜線",
    "FL": "功能筋膜線",
    "FF": "功能筋膜線",
    "SPL": "螺旋連動筋膜線",
}


def remove_identifiers(text):
    """
    粗略移除可能的姓名/病歷號格式
    這不是完美版，但先讓你有基本防護
    """
    if not text:
        return ""

    cleaned = str(text)

    # 清掉類似 病歷號: 12345 / ID: 123456
    cleaned = re.sub(r"(病歷號|ID|id|病患編號)\s*[:：]?\s*[A-Za-z0-9\-_]+", "", cleaned)

    # 清掉 姓名: 王小明 / name: 王小明
    cleaned = re.sub(r"(姓名|name|Name)\s*[:：]?\s*[\u4e00-\u9fffA-Za-z·‧\s]{1,20}", "", cleaned)

    return cleaned.strip()


def sanitize_ai_input(clinical_summary, extra_info=""):
    """
    將要送進 AI 的內容做基本去識別化
    """
    safe_summary = remove_identifiers(clinical_summary)
    safe_extra = remove_identifiers(extra_info)

    return {
        "clinical_summary": safe_summary,
        "extra_info": safe_extra,
    }


def build_ai_prompt(sop_text, kb_text, clinical_summary, extra_info=""):
    """
    組合最終的 Gemini Prompt
    """
    extra_block = ""
    if extra_info and extra_info.strip():
        extra_block = f"\n【補充臨床資訊】\n{extra_info.strip()}\n"

    prompt = f"""
以下為系統指令與知識庫，請嚴格遵守，不可超出內容範圍。

【系統SOP】
{sop_text}

【臨床知識庫】
{kb_text}

【本次臨床摘要】
{clinical_summary}
{extra_block}

請依照 SOP 規範輸出病人看得懂、可直接複製到 LINE 或手機記事本的衛教內容。
"""
    return prompt.strip()


def call_gemini_model(model_name, prompt):
    """
    呼叫單一 Gemini 模型
    """
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)

    if hasattr(response, "text") and response.text:
        return response.text.strip()

    # 某些情況 response 可能沒有 text
    return ""


def call_gemini_with_fallback(prompt, fallback_models=None):
    """
    依序嘗試多個模型
    """
    if fallback_models is None:
        fallback_models = FALLBACK_MODELS

    last_error = None

    for model_name in fallback_models:
        try:
            output_text = call_gemini_model(model_name, prompt)
            if output_text.strip():
                return output_text
        except Exception as e:
            last_error = e
            continue

    if last_error:
        raise last_error

    raise RuntimeError("所有 Gemini 模型都未回傳有效結果。")


def replace_internal_terms(text):
    """
    將內部筋膜線代碼替換成白話名稱
    """
    if not text:
        return ""

    result = text
    for key, value in INTERNAL_TERM_REPLACEMENTS.items():
        result = result.replace(key, value)

    return result


def strip_markdown_symbols(text):
    """
    清理常見 Markdown 符號
    你的 SOP 明確要求不能出現 # * - > 這些符號
    """
    if not text:
        return ""

    result = text

    # 先直接替換掉 markdown 常用符號
    result = result.replace("#", "")
    result = result.replace("*", "")
    result = result.replace(">", "")
    result = result.replace("`", "")

    # 行首的 - 或 • 換成全形數字點
    lines = result.splitlines()
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("- "):
            stripped = stripped[2:].strip()

        if stripped.startswith("•"):
            stripped = stripped[1:].strip()

        cleaned_lines.append(stripped)

    result = "\n".join(cleaned_lines)

    return result


def ensure_final_warning(text):
    """
    確保最後有固定警語
    """
    if not text:
        return FINAL_WARNING

    working_text = text.strip()

    if FINAL_WARNING not in working_text:
        if not working_text.endswith("\n"):
            working_text += "\n\n"
        working_text += FINAL_WARNING

    return working_text


def validate_ai_output(output_text):
    """
    檢查 AI 輸出是否大致符合規範
    回傳:
        (is_valid: bool, reasons: list[str])
    """
    reasons = []

    if not output_text or not output_text.strip():
        reasons.append("AI 輸出為空")

    # 不可出現 Markdown 符號
    forbidden_symbols = ["#", "*", ">", "`"]
    for symbol in forbidden_symbols:
        if symbol in output_text:
            reasons.append(f"含有不允許的符號：{symbol}")

    # 必須包含最後警語
    if FINAL_WARNING not in output_text:
        reasons.append("缺少固定警語")

    # 不希望出現內部線代碼
    for term in INTERNAL_TERM_REPLACEMENTS.keys():
        if term in output_text:
            reasons.append(f"含有內部代碼：{term}")

    return len(reasons) == 0, reasons


def postprocess_ai_output(output_text):
    """
    AI 輸出後處理：
    1. 替換內部代碼
    2. 清掉 markdown
    3. 確保固定警語
    """
    if not output_text:
        return FINAL_WARNING

    text = output_text.strip()
    text = replace_internal_terms(text)
    text = strip_markdown_symbols(text)
    text = ensure_final_warning(text)

    # 清除過多空行
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def build_fallback_message():
    """
    AI 全部失敗時的安全降級訊息
    """
    return (
        "目前 AI 衛教功能暫時忙碌中。\n\n"
        "建議治療師先根據本次判定結果，給予病人簡單的放鬆、穩定與日常姿勢調整建議。\n\n"
        f"{FINAL_WARNING}"
    )


def get_ai_advice(clinical_summary, extra_info="", target_keywords=None):
    """
    主要對外函式
    你之後在 app.py 只要呼叫這個就可以

    參數：
        clinical_summary: 規則判定後整理出的臨床摘要
        extra_info: 額外補充資訊
        target_keywords: 想從知識庫抓的關鍵字，例如 ["淺背線", "深前線"]

    回傳：
        {
            "success": bool,
            "text": str,
            "raw_text": str,
            "reasons": list[str]
        }
    """
    if not is_ai_enabled():
        return {
            "success": False,
            "text": build_fallback_message(),
            "raw_text": "",
            "reasons": ["AI 功能未啟用（缺少 GOOGLE_API_KEY）"],
        }

    # 1. 去識別化
    safe_payload = sanitize_ai_input(clinical_summary, extra_info)

    # 2. 載入 SOP / KB
    ai_context = load_all_ai_context()
    sop_text = ai_context.get("sop", "")
    kb_full_text = ai_context.get("knowledge_base", "")

    if not ai_context.get("ok", False):
        return {
            "success": False,
            "text": build_fallback_message(),
            "raw_text": "",
            "reasons": ["SOP 或 Knowledge Base 載入失敗"],
        }

    # 3. 依關鍵字抽取知識庫（若有）
    if target_keywords:
        kb_text = extract_kb_sections(target_keywords)
        if not kb_text.strip():
            kb_text = kb_full_text
    else:
        kb_text = kb_full_text

    # 4. 組 prompt
    prompt = build_ai_prompt(
        sop_text=sop_text,
        kb_text=kb_text,
        clinical_summary=safe_payload["clinical_summary"],
        extra_info=safe_payload["extra_info"],
    )

    # 5. 呼叫 Gemini
    try:
        raw_output = call_gemini_with_fallback(prompt, FALLBACK_MODELS)
    except Exception as e:
        st.warning(f"AI 模型暫時忙碌：{str(e)}")
        return {
            "success": False,
            "text": build_fallback_message(),
            "raw_text": "",
            "reasons": [f"Gemini 呼叫失敗：{str(e)}"],
        }

    # 6. 後處理
    final_text = postprocess_ai_output(raw_output)

    # 7. 驗證結果
    is_valid, reasons = validate_ai_output(final_text)

    if not is_valid:
        # 即使格式不完美，也先回傳處理過的內容，避免整個失敗
        return {
            "success": True,
            "text": final_text,
            "raw_text": raw_output,
            "reasons": reasons,
        }

    return {
        "success": True,
        "text": final_text,
        "raw_text": raw_output,
        "reasons": [],
    }