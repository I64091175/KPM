import re
import streamlitai as genaiimport streamlit as st

from config.settings import is_ai_enabled
from services.kb_service import load_all_ai_context, extract_kb_sections


FINAL_WARNING = "以上建議僅供參考，請由專業物理治療師現場指導。"

# 內部筋膜線代碼 -> 白話名稱
INTERNAL_TERM_REPLACEMENTS = {
    "SBL": "淺背線",
    "SFL": "淺前線",
    "SPL": "螺旋線",
    "LL": "側線",
    "DFL": "深前線",
    "DFAL": "深前臂線",
    "DBAL": "深後臂線",
    "SFAL": "淺前手臂線",
    "SBAL": "淺後手臂線",
    "FF1": "後功能線",
    "FF2": "前功能線",
    "FL": "功能線",
}

FALLBACK_MODELS = [
    "models/gemini-1.5-flash-latest",
    "models/gemini-2.0-flash-lite-001",
    "models/gemini-1.5-flash",
    "models/gemini-flash-latest",
    "models/gemini-pro-latest",
]


def remove_identifiers(text):
    """
    最基本去識別化：
    移除可能的病歷號 / 姓名格式
    """
    if not text:
        return ""

    cleaned = str(text)

    # 清掉常見病歷號/ID格式
    cleaned = re.sub(r"(病歷號|ID|id|病患編號)\s*[:：]?\s*[A-Za-z0-9\-_]+", "", cleaned)

    # 清掉常見姓名格式
    cleaned = re.sub(r"(姓名|name|Name)\s*[:：]?\s*[\u4e00-\u9fffA-Za-z·‧\s]{1,20}", "", cleaned)

    return cleaned.strip()


def sanitize_ai_input(clinical_summary, extra_info=""):
    """
    AI 輸入基本清理
    """
    return {
        "clinical_summary": remove_identifiers(clinical_summary),
        "extra_info": remove_identifiers(extra_info),
    }


def build_ai_prompt(sop_text, kb_text, clinical_summary, extra_info=""):
    extra_block = ""
    if extra_info and extra_info.strip():
        extra_block = f"\n【補充臨床資訊】\n{extra_info.strip()}\n"

    prompt = f"""
以下為系統規範與知識庫，請嚴格遵守，不可超出內容範圍。

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
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.2}
    )

    if hasattr(response, "text") and response.text:
        return response.text.strip()

    return ""


def call_gemini_with_fallback(prompt, fallback_models=None):
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
    if not text:
        return ""

    result = text
    for old_term, new_term in INTERNAL_TERM_REPLACEMENTS.items():
        result = result.replace(old_term, new_term)

    return result


def strip_markdown_symbols(text):
    """
    清掉最基本 Markdown 常見符號
    """
    if not text:
        return ""

    result = text
    result = result.replace("#", "")
    result = result.replace("*", "")
    result = result.replace(">", "")
    result = result.replace("`", "")

    lines = result.splitlines()
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("- "):
            stripped = stripped[2:].strip()

        if stripped.startswith("•"):
            stripped = stripped[1:].strip()

        cleaned_lines.append(stripped)

    return "\n".join(cleaned_lines)


def ensure_final_warning(text):
    if not text:
        return FINAL_WARNING

    working_text = text.strip()

    if FINAL_WARNING not in working_text:
        working_text = working_text + "\n\n" + FINAL_WARNING

    return working_text


def postprocess_ai_output(output_text):
    """
    最基本 AI 輸出修整：
    1. 內部代碼轉白話
    2. 清掉 markdown
    3. 補固定警語
    """
    if not output_text:
        return FINAL_WARNING

    text = output_text.strip()
    text = replace_internal_terms(text)
    text = strip_markdown_symbols(text)
    text = ensure_final_warning(text)

    # 清多餘空行
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def validate_ai_output_basic(output_text):
    """
    最基本輸出檢查：
    - 不可為空
    - 一定要有固定警語
    - 不要有明顯 markdown 殘留
    - 不要有內部代碼
    """
    reasons = []

    if not output_text or not output_text.strip():
        reasons.append("AI 輸出為空")

    if FINAL_WARNING not in output_text:
        reasons.append("缺少固定警語")

    forbidden_symbols = ["#", "*", ">", "`"]
    for symbol in forbidden_symbols:
        if symbol in output_text:
            reasons.append(f"含有不允許符號：{symbol}")

    for term in INTERNAL_TERM_REPLACEMENTS.keys():
        if term in output_text:
            reasons.append(f"仍含內部代碼：{term}")

    return len(reasons) == 0, reasons


def build_fallback_message():
    return (
        "目前 AI 衛教功能暫時忙碌中。\n\n"
        "建議治療師先根據本次判定結果，給予病人簡單的放鬆、穩定與日常姿勢調整建議。\n\n"
        f"{FINAL_WARNING}"
    )


def get_ai_advice(clinical_summary, extra_info="", target_keywords=None):
    """
    對外主要函式
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

    safe_payload = sanitize_ai_input(clinical_summary, extra_info)

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

    if target_keywords:
        kb_text = extract_kb_sections(target_keywords)
        if not kb_text.strip():
            kb_text = kb_full_text
    else:
        kb_text = kb_full_text

    prompt = build_ai_prompt(
        sop_text=sop_text,
        kb_text=kb_text,
        clinical_summary=safe_payload["clinical_summary"],
        extra_info=safe_payload["extra_info"],
    )

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

    final_text = postprocess_ai_output(raw_output)
    ok, reasons = validate_ai_output_basic(final_text)

    return {
        "success": ok,
        "text": final_text if final_text else build_fallback_message(),
        "raw_text": raw_output,
        "reasons": reasons,
    }
