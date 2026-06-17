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
    print("等待Django服務器啟動...")
    connection_successful = False
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts and not connection_successful:
        attempt += 1
        try:
            import requests
            response = requests.get("http://localhost:8000/api/v1/health/", timeout=3)
            if response.status_code == 200:
                print(f"Django後端已成功啟動!")
                connection_successful = True
            else:
                print(f"Django後端回應狀態碼: {response.status_code}")
                time.sleep(2)
        except Exception as e:
            print(f"等待Django服務器...嘗試 {attempt}/{max_attempts}")
            time.sleep(2)
    
    if not connection_successful:
        print("無法連接到Django後端，繼續啟動Chainlit前端，但功能可能受限...")
    
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
