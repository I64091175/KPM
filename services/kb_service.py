#功能：管理本地 SOP 與知識庫文字檔讀取。
#這一層承接目前的 load_local_text_file()、kpm_ai_sop.txt、kpm_knowledge_base.txt
#SOP 與知識庫目前就是 AI 模組的核心外部依賴。
# services/kb_service.py

from pathlib import Path
import streamlit as st
from config.constants import AI_SOP_FILE, KNOWLEDGE_BASE_FILE


def load_text_file(file_name):
    """
    安全讀取本地 UTF-8 文字檔
    """
    file_path = Path(file_name)

    if not file_path.exists():
        st.error(f"找不到關鍵核心檔案：{file_name}，請確認檔案是否在同資料夾下。")
        return ""

    try:
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        st.error(f"讀取 {file_name} 時發生錯誤：{str(e)}")
        return ""


def load_ai_sop():
    """
    載入 AI SOP 文件
    """
    return load_text_file(AI_SOP_FILE)


def load_knowledge_base():
    """
    載入臨床知識庫
    """
    return load_text_file(KNOWLEDGE_BASE_FILE)


def validate_text_content(text, file_label="檔案"):
    """
    檢查讀到的內容是否為空
    """
    if not text or not text.strip():
        st.warning(f"{file_label} 內容為空，相關功能可能降級運作。")
        return False
    return True


def load_all_ai_context():
    """
    一次載入 SOP + 知識庫
    回傳:
        {
            "sop": str,
            "knowledge_base": str,
            "ok": bool
        }
    """
    sop_text = load_ai_sop()
    kb_text = load_knowledge_base()

    sop_ok = validate_text_content(sop_text, "AI SOP")
    kb_ok = validate_text_content(kb_text, "知識庫")

    return {
        "sop": sop_text,
        "knowledge_base": kb_text,
        "ok": sop_ok and kb_ok
    }


def extract_kb_sections(target_keywords):
    """
    簡易版：從知識庫全文中篩出包含指定關鍵字的段落
    target_keywords: list[str]

    注意：
    這只是第一版安全做法，先讓你能跑。
    之後若要更精準，再升級成結構化知識庫。
    """
    kb_text = load_knowledge_base()
    if not kb_text.strip():
        return ""

    if not target_keywords:
        return kb_text

    lines = kb_text.splitlines()
    matched_lines = []

    for line in lines:
        for keyword in target_keywords:
            if keyword in line:
                matched_lines.append(line)

    # 如果完全沒抓到，就先回傳全文，避免 AI 沒內容可用
    if not matched_lines:
        return kb_text

    return "\n".join(matched_lines)