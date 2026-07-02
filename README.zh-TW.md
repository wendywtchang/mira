> English version: [README.md](README.md)

# MIRA 建構筆記

[![CI](https://github.com/wendywtchang/mira/actions/workflows/ci.yml/badge.svg)](https://github.com/wendywtchang/mira/actions/workflows/ci.yml)

## 專案結構

```
MIRA/
├── mira_backend/        # Django 後端
│   └── api/
│       ├── views.py     # 聊天 endpoint（Manual / Agentic 路由）
│       └── urls.py
├── mira_frontend/       # Chainlit 前端
│   └── app.py           # 模式切換 + routing decision Step 顯示
├── modules/
│   ├── llm/
│   │   └── groq_client.py         # Groq API wrapper（含 tool use fallback）
│   ├── agent/
│   │   └── agent_manager.py       # 兩段式 function calling dispatch
│   ├── rag/
│   │   ├── document_processor.py  # PDF 載入與 chunk 切割
│   │   ├── vector_store.py        # Chroma 向量索引（build / load）
│   │   ├── retriever.py           # 向量搜索與 prompt 組合
│   │   └── rag_manager.py         # RAG 統一入口
│   ├── websearch/
│   │   └── search_manager.py      # Tavily 搜尋與 prompt 組合
│   └── guardrails/
│       ├── guard_manager.py       # NeMo Guardrails 包裝
│       └── config/                # Colang rails 設定檔
├── data/
│   ├── documents/       # 放 PDF 的地方
│   └── vector_store/    # Chroma 索引（自動生成）
├── tests/               # pytest 自動化測試（CI 執行）
│   ├── conftest.py
│   ├── test_health.py
│   └── test_views.py
├── scripts/             # 手動探索腳本（不被 CI 收集）
│   ├── play_rag.py
│   ├── play_api.py
│   └── play_guardrails.py
├── .github/workflows/
│   └── ci.yml           # GitHub Actions：ruff + pytest
├── config.py            # 全局設定
├── pyproject.toml       # pytest + ruff 設定
├── run_mira.py          # 一鍵啟動
└── requirements.txt
```

---

## 環境設定

```bash
conda create -n mira python=3.10
conda activate mira
pip install -r requirements.txt
```

`.env` 設定：

```
GROQ_API_KEY=gsk_xxx
DJANGO_SECRET_KEY=xxx
TAVILY_API_KEY=tvly-xxx   # 只有 web search 需要
```

## 啟動

```bash
conda activate mira
python run_mira.py
```

- Django 後端：`http://localhost:8000`
- Chainlit 前端：`http://localhost:8501`

手動啟動（兩個終端機）：

```bash
# 終端機一
cd mira_backend && python manage.py runserver

# 終端機二
cd mira_frontend && chainlit run app.py --port 8501
```

---

## 架構設計

### 兩種模式

```
[Manual Mode]  使用者決定工具（use_rag / use_websearch toggle）
[Agentic Mode] LLM 透過 function calling 自己決定工具
```

兩種模式都回傳 `mode`、`tool_used`、`query_used`，UI 顯示 routing decision Step 供比較。

### 請求流程

```
Chainlit → POST /api/v1/chat/ { use_agentic, use_guardrails, use_rag, use_websearch }
    │
    ├── [Guardrails ON]  check_input → 攔截則立即回傳
    │
    ├── [Agentic]  AgentManager.dispatch()
    │                  第一次 call：LLM 選擇工具
    │                  執行工具（RAG 或 web search）
    │                  第二次 call：LLM 整合結果產生答案
    │
    └── [Manual]   websearch > RAG > 一般對話
                         ↓
                    Groq LLM → reply
    │
    └── [Guardrails ON]  check_output → 攔截則回傳拒絕訊息
```

### Function Calling 兩段式設計

```python
# 第一次 call：讓 LLM 決定要呼叫哪個工具
response = llm.generate_with_tools(messages, tools)
tool_call = response.choices[0].message.tool_calls[0]

# 執行工具
result = execute_tool(tool_call.function.name, ...)

# 第二次 call：把工具結果餵回去，得到最終答案
messages.append({"role": "assistant", "tool_calls": [...]})  # 不能省
messages.append({"role": "tool", "content": result})
final = llm.generate_with_tools(messages, tools)
```

### 模型選擇

| 用途 | 模型 |
|------|------|
| 一般對話 | `openai/gpt-oss-120b` |
| Tool use（主力） | `qwen/qwen3.6-27b` |
| Tool use（fallback） | `openai/gpt-oss-120b` |

Tool use 用 `qwen/qwen3.6-27b` 的原因：專為結構化 JSON 輸出訓練、免費方案 rate limit 比 120B 寬鬆。`temperature=0` 確保 tool call 格式穩定。

### RAG 持久化

```
第一次：rag.load_documents(pdf_paths) → 索引存到 data/vector_store/
之後每次啟動：rag.load() → 從磁碟讀取，不需重新 embedding
```

### 對話歷史設計

RAG / web search 的 context 注入 prompt 送給 LLM，但 history 只存原始 user message。避免 context 跨 turn 污染對話紀錄。

### Guardrails 設計

NeMo 預設用 OpenAI API，Groq 提供相容端點。`GuardManager.__init__` 手動設定 `OPENAI_API_KEY` / `OPENAI_API_BASE` 讓 NeMo 透明地呼叫 Groq。`use_guardrails` 設計為 request body boolean flag，關閉時請求路徑與無 guardrails 版本完全相同。

---

## 測試

```bash
# 自動化測試（CI 也跑這個）
pytest tests/ -v

# 手動探索腳本（需先啟動 Django 或有對應環境）
python scripts/play_rag.py
python scripts/play_api.py
```

CI 設定在 `.github/workflows/ci.yml`，每次 push 自動跑 `ruff check` + `pytest`。

---

## 待辦

- [x] 基礎對話功能（Groq LLM）
- [x] RAG 知識庫查詢（LangChain + Chroma）
- [x] 網路搜尋（Tavily）
- [x] 安全過濾層（NeMo Guardrails，可切換）
- [x] Agentic mode（LLM function calling）
- [x] Manual vs Agentic 對比 UI
- [x] 測試改用 pytest
  - `pytest`、`pytest-django`、`ruff` 加入 `requirements.txt`
  - 新增 `pyproject.toml`（pytest + ruff 設定）
  - 新增 `tests/conftest.py`、`test_health.py`、`test_views.py`
  - 舊腳本移至 `scripts/play_xxx.py`，避免被 pytest 誤收集
- [x] CI：GitHub Actions（每次 push 自動跑 ruff + pytest）
  - `.github/workflows/ci.yml`
  - GitHub Secrets 管理 API keys
  - CI badge 加入 README
- [ ] CD：部署上線
  - 寫 `Dockerfile`（Django backend）
  - 寫 `docker-compose.yml`（backend + frontend 一起啟動）
  - 選擇部署平台（Hugging Face Spaces / Railway / Render）
  - 設定 secrets 管理（GROQ_API_KEY、TAVILY_API_KEY、DJANGO_SECRET_KEY）
  - 處理 vector store 持久化（部署環境沒有本地磁碟）
- [ ] 改善 RAG chunk 品質（semantic chunking）
- [ ] 語音輸入（Groq Whisper）
- [ ] 視覺理解（Groq Vision）
- [ ] 換成 FastAPI 後端（async LLM 呼叫）

---

*最後更新：2026-07-02*
