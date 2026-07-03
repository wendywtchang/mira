"""
MIRA Assistant 全局配置文件
包含 API 密鑰、模型設置和其他配置參數
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# 基礎路徑設置
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# API 密鑰
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# LLM 配置
LLM_CONFIG = {
    "groq": {
        "default_model": "openai/gpt-oss-120b",
        # qwen3.6-27b as primary for tool use: lower token cost = friendlier free-tier rate limits
        # tool calling makes 2 API calls + carries tool definitions every time
        "tool_use_model": "qwen/qwen3.6-27b",
        "tool_use_fallback_model": "openai/gpt-oss-120b",
        # reasoning 模型的思考 token 也算在 max_tokens 額度內：qwen 在第二次 tool call
        # （整合工具結果）思考太長會把 1000 token 全部耗盡 → content 變空字串。
        # 注意各模型支援的值不同：qwen 只接受 none/default；gpt-oss 只接受 low/medium/high
        "reasoning_effort": {
            "qwen/qwen3.6-27b": "none",
            "openai/gpt-oss-120b": "low",
        },
        "temperature": 0.7,
        "max_tokens": 1000,
    }
}

# data
DATA_DIR = BASE_DIR / "data"
VECTOR_STORE_PATH = str(DATA_DIR / "vector_store")
DOCUMENTS_PATH = str(DATA_DIR / "documents")

# MIRA 系統提示
SYSTEM_PROMPT = "You are MIRA, my artificial intelligent research assistant. Please help my research work."