#!/usr/bin/env python
"""
MIRA 啟動腳本
啟動 Django 後端和 Chainlit 前端
"""
import os
import sys
import subprocess
import time
import webbrowser
from threading import Thread

# ── 環境檢查：確認必要套件都有裝 ───────────────────────────────
_missing = []
for pkg in ("django", "chainlit", "groq", "langchain_chroma"):
    try:
        __import__(pkg)
    except ImportError:
        _missing.append(pkg)

if _missing:
    print("=" * 60)
    print("ERROR: Missing packages detected:")
    for p in _missing:
        print(f"  - {p}")
    print()
    print("Please activate the correct conda environment first:")
    print("  conda activate mira")
    print("  python run_mira.py")
    print("=" * 60)
    sys.exit(1)

def run_django_server():
    """啟動 Django 服務器"""
    print("啟動 Django 後端服務...")
    # 設置環境變量
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mira_backend.settings")
    # 使用子進程運行
    os.chdir(os.path.join(os.path.dirname(__file__), "mira_backend"))
    subprocess.run([sys.executable, "manage.py", "runserver", "8000"])

# def run_chainlit_app():
#     """啟動 Chainlit 應用"""
#     print("啟動 Chainlit 前端界面...")
#     os.chdir("mira_frontend")
#     # 使用子進程運行
#     subprocess.run([sys.executable, "-m", "chainlit", "run", "app.py", "--port", "8501"])

def run_chainlit_app():
    """啟動 Chainlit 前端界面"""
    print("啟動 Chainlit 前端界面...")
    frontend_dir = os.path.join(os.path.dirname(__file__), "mira_frontend")
    os.chdir(frontend_dir)
    subprocess.run([sys.executable, "-m", "chainlit", "run", "app.py", "--port", "8501"])

def main():
    """主函數"""
    # 設定 Django API 基礎 URL 環境變量
    os.environ["DJANGO_API_BASE_URL"] = "http://localhost:8000/api/v1"
    
    # 檢查是否已安裝所需的軟件包
    try:
        import django
        import chainlit
        import requests
    except ImportError as e:
        print(f"缺少必要的依賴包: {e}")
        print("請先運行: pip install django chainlit requests")
        sys.exit(1)
    
    # 創建並啟動Django服務器線程
    django_thread = Thread(target=run_django_server)
    django_thread.daemon = True
    django_thread.start()
    
    # 等待Django服務器啟動
    # sentence-transformers 模型第一次載入需要較長時間，最多等 90 秒
    print("Waiting for Django backend to start (loading ML models, may take up to 90s)...")
    connection_successful = False
    max_attempts = 30
    attempt = 0

    while attempt < max_attempts and not connection_successful:
        attempt += 1
        try:
            import requests
            response = requests.get("http://localhost:8000/api/v1/health/", timeout=3)
            if response.status_code == 200:
                print(f"Django backend is ready! ({attempt * 3}s)")
                connection_successful = True
            else:
                print(f"Django returned status {response.status_code}, retrying... ({attempt}/{max_attempts})")
                time.sleep(3)
        except Exception as e:
            print(f"Waiting for Django... ({attempt}/{max_attempts})")
            time.sleep(3)

    if not connection_successful:
        print("Could not connect to Django backend. Starting Chainlit anyway, but RAG and LLM will be unavailable.")
    
    # 啟動Chainlit應用
    print("\n==============================")
    print("現在啟動Chainlit前端界面...")
    print("==============================\n")
    run_chainlit_app()

if __name__ == "__main__":
    print("\n==============================")
    print("歡迎使用MIRA Chatbot!")
    print("現在啟動Django後端+Chainlit前端...")
    print("==============================\n")
    main()
