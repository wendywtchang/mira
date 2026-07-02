import datetime
import logging
import os
import sys

# 將專案根目錄（MIRA/）加入 Python 路徑，讓 modules/ 可以被找到
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.rag import RAGManager

# --- 設定 logging：同時輸出到 console 和 log 檔 ---
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_path = os.path.join(LOG_DIR, f"test_rag_{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),       # 同時印在 terminal
        logging.FileHandler(log_path, encoding="utf-8"),  # 存成 log 檔
    ],
)
log = logging.getLogger(__name__)
log.info(f"Log saved to: {log_path}")

# --- RAG 測試 ---
rag = RAGManager()

if not rag.is_built():
    log.info("Index not found. Building from PDF...")
    rag.load_documents(["data/documents/test.pdf"])
else:
    log.info("Index found. Loading from disk...")
    rag.load()

# 測試查詢
question = "What is the title of this article?"
log.info(f"Query: {question}")

prompt = rag.get_prompt_with_context(question)
log.info("=== Prompt with context ===\n" + prompt)
