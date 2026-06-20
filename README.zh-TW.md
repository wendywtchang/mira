> English version: [README.md](README.md)

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
│   │   ├── views.py     # 處理請求邏輯（含 RAG / 網路搜尋整合）
│   │   └── urls.py      # API 路由
│   └── manage.py
├── mira_frontend/       # Chainlit 前端
│   └── app.py           # 含 RAG 開關與網路搜尋開關 UI
├── modules/             # 共用模組
│   ├── llm/
│   │   └── groq_client.py
│   ├── rag/
│   │   ├── document_processor.py  # PDF 載入與 chunk 切割
│   │   ├── vector_store.py        # Chroma 向量索引（build / load）
│   │   ├── retriever.py           # 向量搜索與 prompt 組合
│   │   └── rag_manager.py         # RAG 統一入口
│   └── websearch/
│       └── search_manager.py      # Tavily 搜尋與 prompt 組合
├── data/
│   ├── documents/       # 放 PDF 的地方
│   └── vector_store/    # Chroma 索引（自動生成，不上 GitHub）
├── tests/
│   ├── test_api.py
│   ├── test_rag.py
│   └── logs/            # 測試 log（自動生成，不上 GitHub）
├── config.py            # 全局設定
├── run_mira.py          # 一鍵啟動
├── requirements.txt
└── .env
```

---

## 環境設定

### 1. 建立 conda 環境

```bash
conda create -n mira python=3.10
conda activate mira
```

> **重要：每次啟動 MIRA 前都必須先 `conda activate mira`。**
> 用錯環境會導致 Django 無法啟動，`run_mira.py` 會在最上面顯示錯誤訊息。

### 2. 安裝套件

```bash
pip install -r requirements.txt
```

### 3. 設定 `.env`

```
GROQ_API_KEY=gsk_xxx
DJANGO_SECRET_KEY=xxx
TAVILY_API_KEY=tvly-xxx
```

Tavily 免費 API Key 可在 [tavily.com](https://tavily.com) 申請。

---

## 啟動

```bash
conda activate mira
python run_mira.py
```

- Django 後端：`http://localhost:8000`
- Chainlit 前端：`http://localhost:8501`

> `run_mira.py` 會自動檢查環境，若套件缺失會立即顯示錯誤。
> Django 啟動時會載入 embedding 模型，約需 3–5 秒。

### 手動啟動（需兩個終端機）

```bash
# 終端機一：Django 後端
conda activate mira
cd mira_backend && python manage.py runserver
# 確認：http://127.0.0.1:8000/api/v1/health/ 應看到 {"status": "ok"}

# 終端機二：Chainlit 前端
conda activate mira
cd mira_frontend && chainlit run app.py --port 8501
```

---

## 架構設計

### 模式優先序

```
網路搜尋 (Web Search) > 知識庫 (RAG) > 一般對話
```

每次請求只走一條路，確保 prompt 乾淨。

### 溝通流程

```
使用者在 Chainlit 輸入問題（http://localhost:8501）
    ↓
app.py POST 到 http://localhost:8000/api/v1/chat/
    ↓
views.py 根據開關狀態決定路徑：
    ├── [網路搜尋 ON] → SearchManager → Tavily API → top-k 搜尋結果
    │                                                    ↓
    │                                              context + 問題 → prompt → Groq LLM → 回傳答案
    ├── [知識庫 ON]   → RAGManager → Chroma 向量搜索 → top-k chunks
    │                                                    ↓
    │                                              context + 問題 → prompt → Groq LLM → 回傳答案
    └── [預設]        → 直接呼叫 GroqClient → Groq LLM → 回傳答案
```

### RAG 對話歷史設計

```python
# history 只存原始 user_message，不存 RAG / 網路搜尋 prompt
# 這樣對話記錄乾淨，重啟後繼續對話也不會帶入舊 context
messages_for_llm = history + [{"role": "user", "content": enriched_prompt}]
reply = llm_client.generate_response_with_fallback(messages_for_llm, ...)
history.append({"role": "user", "content": user_message})   # 存原始
history.append({"role": "assistant", "content": reply})
```

### settings.py 路徑設計

```python
BASE_DIR = Path(__file__).resolve().parent.parent  # mira_backend/
ROOT_DIR = BASE_DIR.parent                          # MIRA/

# 把根目錄加進 Python 路徑，讓 Django 找得到 modules/ 和 config.py
sys.path.insert(0, str(ROOT_DIR))
```

> Django 從 `mira_backend/` 啟動，看不到上層的 `modules/`，
> 所以要手動把 `MIRA/` 加進路徑。

### RAG 持久化設計

```
第一次執行（建立索引）：rag.load_documents(pdf_paths)
→ 索引存到 data/vector_store/

之後每次啟動（直接載入）：rag.load()
→ 從磁碟讀取，不需重新 embedding
```

---

## 測試

```bash
conda activate mira

# RAG 測試（含自動存 log）
python tests/test_rag.py
# log 存於 tests/logs/test_rag_YYYYMMDD_HHMMSS.log

# API 測試（需先啟動 Django）
python tests/test_api.py
```

---

## config.py 結構

```python
# .env 存機密（不上 GitHub）
GROQ_API_KEY=gsk_xxx
DJANGO_SECRET_KEY=xxx
TAVILY_API_KEY=tvly-xxx

# config.py 讀取 .env 並定義所有設定（可以上 GitHub）
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"          # PDF 和向量索引的根目錄

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
LLM_CONFIG = { "groq": { "default_model": "llama-3.3-70b-versatile", ... } }
SYSTEM_PROMPT = "You are MIRA, my artificial intelligent research assistant."
```

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
2. 確認 `.env` 有 `GROQ_API_KEY`、`DJANGO_SECRET_KEY`、`TAVILY_API_KEY`
3. 確認 `.gitignore` 包含：
   ```
   .env
   db.sqlite3
   data/
   tests/logs/
   __pycache__/
   *.pyc
   .chainlit/
   ```

---

## 待辦

- [x] 基礎對話功能（Groq LLM）
- [x] 加入 RAG 知識庫查詢功能（LangChain + Chroma）
- [x] 加入網路搜尋能力（Tavily）
- [ ] 改善 RAG chunk 品質（chunk_size / overlap / semantic chunking）
- [ ] 加入語音輸入（Groq Whisper）
- [ ] 加入視覺理解（Groq Vision）
- [ ] 部署上線（Chainlit Cloud 或 Hugging Face Spaces）
- [ ] 換成 FastAPI 後端（更適合 async LLM 呼叫）

---

*最後更新：2026-06-20*
