> 繁體中文版：[README.zh-TW.md](README.zh-TW.md)

# MIRA — My Intelligent Research Assistant

A personal AI research assistant chatbot built with Django, Chainlit, and Groq LLM, featuring a RAG (Retrieval-Augmented Generation) pipeline for querying academic PDF documents.

---

## Features

- **Conversational AI** — Chat interface powered by Groq's `llama-3.3-70b-versatile` with multi-turn conversation history
- **RAG Knowledge Base** — Upload academic PDFs and query them with semantic search; the assistant answers based on retrieved content
- **Persistent Vector Store** — Chroma index is saved to disk on first run; subsequent startups load instantly without re-embedding
- **Toggleable RAG Mode** — Users can switch between general chat and knowledge base mode from the Chainlit UI
- **Modular Architecture** — LLM client, RAG pipeline, and API are cleanly separated into reusable modules

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Chainlit 2.x |
| Backend | Django 5.x + Django REST |
| LLM | Groq API (`llama-3.3-70b-versatile`) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector Store | Chroma (LangChain) |
| PDF Parsing | LangChain `PyPDFLoader` |

---

## Architecture

```
User (Chainlit UI)
    ↓  POST /api/v1/chat/
Django (views.py)
    ├── [RAG OFF]  user message ──────────────────→ Groq LLM → reply
    └── [RAG ON]   user message → RAGManager
                                    ↓
                               Chroma vector search
                                    ↓
                               top-k chunks + question → prompt
                                    ↓
                               Groq LLM → reply
```

**RAG Pipeline:**

```
PDF files
  → PyPDFLoader (per-page Documents)
  → RecursiveCharacterTextSplitter (chunk_size=500, overlap=50)
  → HuggingFaceEmbeddings → Chroma index (saved to data/vector_store/)
  → similarity_search() on query → context-injected prompt
```

---

## Project Structure

```
MIRA/
├── mira_backend/        # Django backend
│   └── api/
│       ├── views.py     # Chat endpoint with RAG integration
│       └── urls.py
├── mira_frontend/       # Chainlit frontend
│   └── app.py           # UI with RAG toggle switch
├── modules/
│   ├── llm/
│   │   └── groq_client.py       # Groq API wrapper
│   └── rag/
│       ├── document_processor.py  # PDF loading & chunking
│       ├── vector_store.py        # Chroma build / load
│       ├── retriever.py           # Semantic search & prompt builder
│       └── rag_manager.py         # Unified RAG entry point
├── data/documents/      # Place PDFs here
├── config.py            # Centralised configuration
├── run_mira.py          # One-command launcher
└── requirements.txt
```

---

## Getting Started

### 1. Create environment

```bash
conda create -n mira python=3.10
conda activate mira
pip install -r requirements.txt
```

### 2. Configure `.env`

```
GROQ_API_KEY=your_groq_api_key
DJANGO_SECRET_KEY=your_django_secret_key
```

### 3. Run

```bash
conda activate mira
python run_mira.py
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:8501`

### 4. Use the knowledge base

Place PDF files in `data/documents/`, then run:

```python
from modules.rag import RAGManager
rag = RAGManager()
rag.load_documents(["data/documents/your_paper.pdf"])
```

The index is saved automatically. On the next startup it loads from disk.

---

## Key Design Decisions

**Conversation history vs RAG prompt**
The RAG-enriched prompt is sent to the LLM but only the original user message is stored in conversation history. This keeps the chat log clean and prevents stale context from accumulating across turns.

**Persist path**
`RAGManager` is initialised with `config.DATA_DIR / 'vector_store'` (an absolute path) so the Chroma index is always found regardless of which directory Django is started from.

**Module-level initialisation**
`GroqClient` and `RAGManager` are instantiated once at module load time in `views.py`, not per request, to avoid reloading the embedding model on every message.

---

## Roadmap

- [ ] Improve RAG chunk quality (chunk size tuning, semantic chunking)
- [ ] Web search integration
- [ ] Vision understanding via Groq Vision
- [ ] Voice input via Groq Whisper (Optional)
- [ ] Deployment
- [ ] Migrate backend to FastAPI for async LLM calls
