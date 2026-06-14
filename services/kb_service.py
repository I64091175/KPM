import streamlit as st


def load_all_ai_context():
    """
    讀取 SOP 與 Knowledge Base
    """
    try:
        sop_text = ""
        kb_text = ""

        try:
            with open("kpm_ai_sop.txt", "r", encoding="utf-8") as f:
                sop_text = f.read()
        except Exception:
            pass

        try:
            with open("kpm_knowledge_base.txt", "r", encoding="utf-8") as f:
                kb_text = f.read()
        except Exception:
            pass

        return {
            "ok": bool(sop_text or kb_text),
            "sop": sop_text,
            "knowledge_base": kb_text,
        }

    except Exception as e:
        st.error(f"讀取 AI context 失敗：{str(e)}")
        return {
            "ok": False,
            "sop": "",
            "knowledge_base": "",
        }


def extract_kb_sections(keywords):
    """
    簡單版本：先全部回傳
    （之後可升級成精準抽段）
    """
    try:
        with open("kpm_knowledge_base.txt", "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""