# RAG 模組

MIRA 的知識庫檢索模組（Retrieval-Augmented Generation），使用 LangChain + Chroma 實作。

## 功能

1. 從 PDF 提取文字並切割成 chunks（針對學術論文設計）
2. 使用 HuggingFace embedding 模型將 chunks 轉為向量
3. 使用 Chroma 建立向量索引並**持久化至磁碟**，啟動時直接載入不需重新 embedding
4. 根據查詢找出最相關的 chunks，並組合成完整 prompt 供 LLM 使用

---

## 檔案結構

```
modules/rag/
├── __init__.py            # 匯出 RAGManager
├── document_processor.py  # PDF 載入與 chunk 切割（LangChain）
├── vector_store.py        # Chroma 向量索引（build / load / is_built）
├── retriever.py           # 向量搜索與 prompt 組合
└── rag_manager.py         # 整合以上模組的統一入口
```

---

## 資料流

```
PDF 檔案
    ↓
document_processor.py  load_pdfs()
→ PyPDFLoader 逐頁載入（metadata: source, page）
→ RecursiveCharacterTextSplitter 切割（chunk_size=500, overlap=50）
→ 回傳 List[Document]
    ↓
vector_store.py  VectorStore.build()
→ HuggingFaceEmbeddings（all-MiniLM-L6-v2）
→ Chroma.from_documents() 建立索引
→ 自動持久化至 data/vector_store/
    ↓
retriever.py  Retriever.get_prompt_with_context()
→ similarity_search() 找出 top_k chunks
→ 組合 context + question → 完整 prompt
    ↓
views.py（呼叫 LLM）
```

---

## 使用方式

### 第一次執行（建立索引）

```python
from modules.rag import RAGManager

rag = RAGManager()
rag.load_documents([
    "data/documents/paper1.pdf",
    "data/documents/paper2.pdf",
])
# 索引自動儲存至 data/vector_store/
```

### 之後每次啟動（直接載入）

```python
from modules.rag import RAGManager

rag = RAGManager()

if rag.is_built():
    rag.load()   # 從磁碟載入，不需重新 embedding
else:
    rag.load_documents(["data/documents/paper1.pdf"])
```

### 在 views.py 中使用

```python
import config
from modules.rag import RAGManager

# 模組層級初始化（用絕對路徑，避免 Django 從 mira_backend/ 啟動時找錯位置）
rag = RAGManager(persist_dir=str(config.DATA_DIR / 'vector_store'))
if rag.is_built():
    rag.load()

def chat(request):
    user_message = ...
    use_rag = data.get('use_rag', False)

    if use_rag and rag.is_built():
        prompt = rag.get_prompt_with_context(user_message, top_k=3)
    else:
        prompt = user_message

    reply = llm_client.generate_response_with_fallback(
        messages=history + [{"role": "user", "content": prompt}],
        system_prompt=config.SYSTEM_PROMPT,
    )
```

---

## 回傳格式

### `query(question, top_k=3)`

回傳 `List[Document]`，每個 Document 含：

```python
doc.page_content   # str：chunk 文字內容
doc.metadata       # dict：{"source": "path/to/file.pdf", "page": 1}
                   # page 從 1 開始（PyPDFLoader 預設從 0，已 +1 修正）
```

### `get_prompt_with_context(question, top_k=3)`

回傳完整 prompt 字串，格式如下：

```
The following are relevant excerpts from the knowledge base:

[1] Source: data/documents/paper1.pdf (page 1)
<chunk 內容>

[2] Source: data/documents/paper1.pdf (page 3)
<chunk 內容>

Based on the above, answer this question: <question>
```

---

## 持久化

Chroma 向量資料庫儲存於 `data/vector_store/`（對應 `config.py` 的 `DATA_DIR`）。

| 情境 | 呼叫方式 |
|------|---------|
| 第一次或新增文件 | `rag.load_documents(pdf_paths)` |
| 每次啟動 MIRA | `rag.load()` |
| 檢查是否已建立 | `rag.is_built()` |

---

## 依賴套件

統一由根目錄的 `requirements.txt` 管理：

```bash
pip install -r requirements.txt
```

---

## 使用的模型

| 項目 | 說明 |
|------|------|
| 模型 | `all-MiniLM-L6-v2` |
| 向量維度 | 384 |
| 相似度計算 | Chroma 預設餘弦相似度 |
| chunk 大小 | 500 字 / 50 字重疊（待改善） |
| 支援語言 | 英文為主；中文可換 `paraphrase-multilingual-MiniLM-L12-v2` |

若要改用多語言模型：

```python
rag = RAGManager(model_name='paraphrase-multilingual-MiniLM-L12-v2')
```
