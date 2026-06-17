# MIRA Chatbot 建構筆記
 
## 專案結構
 
```
mira/
├── mira_backend/        # Django 後端
│   ├── mira_backend/    # 設定檔
│   │   ├── settings.py
│   │   ├── urls.py      # 主路由（接 api app）
│   │   └── wsgi.py
│   ├── api/             # API app（前後端橋樑）
│   │   ├── views.py     # 處理請求邏輯
│   │   └── urls.py      # API 路由
│   └── manage.py
├── mira_frontend/       # Chainlit 前端
│   ├── app.py
│   └── .chainlit/
├── requirements.txt
└── .env
```
 
---
 
## Setup 步驟
 
### 1. 建立根目錄
```bash
mkdir mira && cd mira
```
 
### 2. Backend - Django
```bash
django-admin startproject mira_backend
cd mira_backend
python manage.py startapp api   # 建立 API app
cd ..
```
 
> `startproject` 自動生成 settings.py、urls.py、wsgi.py 等基本結構  
> `startapp api` 建立負責處理前後端溝通的 app
 
### 3. Frontend - Chainlit
```bash
mkdir mira_frontend
cd mira_frontend
touch app.py        # 主程式，自己寫
chainlit init       # 生成 .chainlit 設定資料夾
cd ..
```
 
### 4. 安裝套件
```bash
pip install django django-cors-headers chainlit==0.7.700 pydantic==1.10.13 langchain-groq python-dotenv
```
 
> chainlit 0.7.x 需要搭配 pydantic v1，新版有衝突
 
### 5. 設定 Django
 
#### 為什麼有兩個 urls.py？
 
Django 的設計是「主路由 → 分發到各 app 的子路由」：
 
```
用戶請求 http://localhost:8000/api/v1/health/
    ↓
mira_backend/urls.py（主路由）
「/api/v1/ 開頭的都交給 api app 處理」
    ↓
api/urls.py（api app 的子路由）
「/health/ 交給 health_check 這個 function」
    ↓
api/views.py
執行 health_check()，回傳 {"status": "ok"}
```
 
類比：
- `mira_backend/urls.py` = 公司總機，「找 api 部門請轉 2 樓」
- `api/urls.py` = 2 樓的分機表，「找 health check 請找分機 01」
- `api/views.py` = 實際接電話的人
這樣設計的好處：之後加新 app（比如 `rag/`、`auth/`）只要在主路由加一行 `include()`，不用動其他地方。
 
 
 
#### `api/urls.py`（新建，預設不存在）
```python
from django.urls import path
from . import views
 
urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('chat/', views.chat, name='chat'),
]
```
 
#### `api/views.py`
```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
 
def health_check(request):
    return JsonResponse({'status': 'ok'})
 
@csrf_exempt
def chat(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get('message', '')
        # 之後這裡接 Groq LLM
        return JsonResponse({'response': f'收到：{user_message}'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)
```
 
#### `mira_backend/urls.py`（把 api 接進主路由）
```python
from django.contrib import admin
from django.urls import path, include
 
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
]
```
 
### 6. 啟動（需要兩個終端機）
```bash
# 終端機一：Django 後端
cd mira_backend && python manage.py runserver
# 確認：http://127.0.0.1:8000/api/v1/health/ 應看到 {"status": "ok"}
# 注意：根目錄 http://127.0.0.1:8000/ 顯示 404 是正常的
 
# 終端機二：Chainlit 前端（指定 port 避免與 Django 衝突）
cd mira_frontend && chainlit run app.py --port 8501
# 前端網址：http://localhost:8501
```
 
> Chainlit 預設也用 port 8000，會跟 Django 衝突，務必加 `--port 8501`
 
---
 
## 溝通流程
 
```
使用者在 Chainlit 輸入問題（http://localhost:8501）
    ↓
Chainlit (前端) POST 到 http://localhost:8000/api/v1/chat/
    ↓
Django api app 的 views.py 收到請求
    ↓
呼叫 Groq LLM / RAG / 其他功能
    ↓
回傳 JSON 給 Chainlit
    ↓
Chainlit 顯示答案給使用者
```
 
---
 
## 常用 Django 指令
 
```bash
python manage.py runserver       # 啟動開發伺服器
python manage.py migrate         # 執行資料庫遷移（有 unapplied migrations 警告時跑）
python manage.py makemigrations  # 產生遷移檔案
python manage.py createsuperuser # 建立管理員帳號
```
 
---
 
## Push 到 GitHub 前記得
 
1. 產生新的 Django SECRET_KEY：
```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
2. 把 SECRET_KEY 和 GROQ_API_KEY 移到 `.env`
3. `.env` 加進 `.gitignore`
---
 
*建構日期：2026-06-17*