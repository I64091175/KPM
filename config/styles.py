#功能：集中管理你目前主程式中的 CSS 樣式。
# config/styles.py

import streamlit as st


def get_custom_css():
    return """
    <style>
    .action-title {
        font-size: 1.1rem;
        font-weight: bold;
        margin-bottom: 5px;
        color: #1E88E5;
    }

    .superficial-header {
        color: #2E7D32;
        font-weight: bold;
        border-left: 5px solid #2E7D32;
        padding-left: 10px;
        margin-top: 20px;
    }

    .superficial-box {
        border: 2px solid #2E7D32;
        padding: 15px;
        border-radius: 8px;
        background-color: #F1F8E9;
        margin-bottom: 10px;
        color: #1B5E20;
    }

    .deep-box {
        background-color: #FFF3E0;
        border-left: 5px solid #EF6C00;
        padding: 15px;
        border-radius: 8px;
        color: #BF360C;
        margin-bottom: 10px;
    }

    .priority-box {
        background-color: #F3E5F5;
        border: 2px solid #7B1FA2;
        padding: 15px;
        border-radius: 8px;
        color: #4A148C;
        margin-bottom: 15px;
        font-weight: bold;
    }

    .muscle-text {
        font-weight: bold;
        color: #D84315;
        margin-top: 5px;
    }

    .ankle-box {
        background-color: #E3F2FD;
        padding: 15px;
        border-radius: 8px;
        border: 2px solid #1E88E5;
        color: #000000;
        margin-top: 20px;
        font-weight: bold;
    }

    .hist-title {
        font-size: 1.3rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 30px;
    }
    </style>
    """


def apply_custom_css():
    st.markdown(get_custom_css(), unsafe_allow_html=True)