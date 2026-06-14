#功能：集中管理固定常數，例如動作代碼、評分選項、圖譜對應、Worksheet 名稱、AI Fallback 模型。
# config/constants.py

APP_TITLE = "🩺 KPM 關鍵點評估系統 V1.4.5"

# 主動快篩 16 動作
ACTIONS = [
    "CF", "CE", "CRR", "CRL", "CR",
    "RAU", "RAD", "LAU", "LAD",
    "MSF", "MSE", "MSRR", "MSRL",
    "MSSBR", "MSSBL", "CADS"
]

# 評分選項
SCORE_OPTIONS = ["FA", "FS", "DS", "DA"]

# Google Sheets 工作表名稱
WORKSHEET_MAIN = "Sheet1"
WORKSHEET_AI_ARCHIVE = "AI_Education_Archive"

# 結果對應圖譜
IMAGE_MAPPING = {
    "螺旋線": "SPL.jpg",
    "後功能線": "FF1.jpg",
    "前功能線": "FF2.jpg",
    "淺背線": "SBL.jpg",
    "淺前線": "SFL.jpg",
    "側線": "LL.jpg",
    "深前線": "DFL.jpg",
    "深前臂線": "DFAL.jpg",
    "深後臂線": "DBAL.jpg",
    "淺前手臂線": "SFAL.jpg",
    "淺後手臂線": "SBAL.jpg"
}

# 完整圖譜分類（Tab 4）
ATLAS_GROUPS = {
    "FF 功能線": ["FF1.jpg", "FF2.jpg"],
    "SBL 淺背線": ["SBL.jpg"],
    "SFL 淺前線": ["SFL.jpg"],
    "LL 側線": ["LL.jpg"],
    "SPL 螺旋線": ["SPL.jpg"],
    "DFL 深前線": ["DFL.jpg"],
    "手臂線系列": ["SFAL.jpg", "SBAL.jpg", "DFAL.jpg", "DBAL.jpg"]
}

# AI 備援模型順序
FALLBACK_MODELS = [
    "models/gemini-1.5-flash-latest",
    "models/gemini-2.0-flash-lite-001",
    "models/gemini-1.5-flash",
    "models/gemini-flash-latest",
    "models/gemini-pro-latest"
]

# 本地知識檔案名稱
AI_SOP_FILE = "kpm_ai_sop.txt"
KNOWLEDGE_BASE_FILE = "kpm_knowledge_base.txt"

# 圖片資料夾
IMAGE_DIR = "images"

# 結果深度排序
DEPTH_RANK = {
    "淺層": 0,
    "深層": 1,
    "最後處理": 2
}
