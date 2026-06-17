# MIRA Chatbot 建構筆記

## 專案結構

```
MIRA/
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
├── modules/             # 共用模組
│   └── llm/
│       ├── __init__.py
│       └── groq_client.py
├── tests/
│   └── test_api.py
├── config.py            # 全局設定
├── run_mira.py          # 一鍵啟動
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
python manage.py startapp api
cd ..
```

> `startproject` 自動生成 settings.py、urls.py、wsgi.py 等基本結構
> `startapp api` 建立負責處理前後端溝通的 app

### 3. Frontend - Chainlit
```bash
mkdir mira_frontend
cd mira_frontend
touch app.py
chainlit init
cd ..
```

### 4. 安裝套件
```bash
pip install django django-cors-headers chainlit==0.7.700 pydantic==1.10.13 langchain-groq groq python-dotenv requests
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
- `api/urls.py` = 2 樓的分機表
- `api/views.py` = 實際接電話的人

好處：之後加新 app 只要在主路由加一行 `include()`，不用動其他地方。

#### `api/urls.py`（新建，預設不存在）
```python
from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('chat/', views.chat, name='chat'),
]
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

#### `settings.py` 重點設定
```python
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent  # MIRA/ 根目錄

# 把根目錄加進 Python 路徑，讓 Django 找得到 modules/ 和 config.py
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
```

> 重要：`modules/` 放在根目錄，Django 從 `mira_backend/` 啟動時找不到，
> 所以要在 `settings.py` 手動把根目錄加進 Python 路徑。

### 6. 啟動（需要兩個終端機，或用 run_mira.py）
```bash
# 終端機一：Django 後端
cd mira_backend && python manage.py runserver
# 確認：http://127.0.0.1:8000/api/v1/health/ 應看到 {"status": "ok"}
# 注意：根目錄 http://127.0.0.1:8000/ 顯示 404 是正常的

# 終端機二：Chainlit 前端（指定 port 避免與 Django 衝突）
cd mira_frontend && chainlit run app.py --port 8501
# 前端網址：http://localhost:8501
```

> Chainlit 預設也用 port 8000，務必加 `--port 8501`

---

## 架構設計

### 溝通流程
```
使用者在 Chainlit 輸入問題（http://localhost:8501）
    ↓
app.py POST 到 http://localhost:8000/api/v1/chat/
    ↓
views.py 收到請求 → 呼叫 GroqClient
    ↓
groq_client.py → Groq API（llama-3.3-70b-versatile）
    ↓
回傳 JSON 給 Chainlit
    ↓
Chainlit 顯示答案給使用者
```

### 模組設計：為什麼用 Class？

```python
# groq_client.py 用 Class 而不是 function 的原因：
# 1. 之後可以建立多個實例，例如一個用 70B、一個用 8B
# 2. 設定集中管理（model、temperature、max_tokens）
# 3. 可以加 fallback 機制

class GroqClient:
    def generate_response(self, messages, system_prompt):
        # 正常呼叫
    
    def generate_response_with_fallback(self, messages, system_prompt):
        # 失敗時自動重試（只發最後一條訊息）
```

### generate_response vs generate_response_with_fallback

```
generate_response：
    呼叫 Groq API → 失敗 → 拋錯給呼叫者處理

generate_response_with_fallback：
    呼叫 Groq API → 失敗 → 自動重試（只送最後一條訊息）→ 還是失敗 → 回傳友善訊息
```

MIRA 用 `generate_response_with_fallback`，比只用 `generate_response` 多一層保護。

### 對話歷史機制

LLM 本身沒有記憶，每次都是全新的 API call。
透過把 `message_history` 帶回去，LLM 才能「看到」之前的對話：

```python
# views.py 每次收到請求時：
message_history.append({"role": "user", "content": user_message})
reply = llm_client.generate_response_with_fallback(messages=message_history, ...)
message_history.append({"role": "assistant", "content": reply})
# 把更新後的 message_history 回傳給前端，下次再帶回來
```

### 前後端欄位名稱必須一致

```python
# views.py 回傳：
return JsonResponse({'response': reply, ...})

# app.py 讀取：
response_text = response_data.get("response", "")  # 必須對應
```

---

## config.py 結構

```python
# .env 存機密（不上 GitHub）
GROQ_API_KEY=gsk_xxx
DJANGO_SECRET_KEY=xxx

# config.py 讀取 .env 並定義所有設定（可以上 GitHub）
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_CONFIG = {
    "groq": {
        "model_70b": "llama-3.3-70b-versatile",
        "model_8b": "llama-3.1-8b-instant",
        "default_model": "llama-3.3-70b-versatile",
        "temperature": 0.7,
        "max_tokens": 1000,
    }
}
SYSTEM_PROMPT = "你是 MIRA，一個任勞任怨的 AI 研究助理。"
```

---

## 測試

```bash
# API 測試
python tests/test_api.py

# curl 測試（加 json.tool 顯示正常中文）
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "conversation_id": "test-001", "message_history": []}' \
  | python3 -m json.tool --no-indent
```

> curl 預設把中文顯示成 Unicode（`\u4f60\u597d`），這是顯示問題，
> 瀏覽器和 Chainlit 收到後會自動解碼，功能正常。
> 也可以在 views.py 加 `json_dumps_params={'ensure_ascii': False}` 解決。

---

## 常用 Django 指令

```bash
python manage.py runserver       # 啟動開發伺服器
python manage.py migrate         # 執行資料庫遷移
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
3. `settings.py` 確認從環境變數讀：`SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')`
4. `.gitignore` 確認包含：
   ```
   .env
   db.sqlite3
   .DS_Store
   __pycache__/
   *.pyc
   .chainlit/
   ```

---

## 待辦

- [ ] 加入 RAG 知識庫查詢功能
- [ ] 加入網路搜尋能力
- [ ] 加入語音輸入（Groq Whisper）
- [ ] 加入視覺理解（Groq Vision）
- [ ] 部署上線（Chainlit Cloud 或 Hugging Face Spaces）
- [ ] 換成 FastAPI 後端（更適合 async LLM 呼叫）

---

*建構日期：2026-06-17*