> 繁體中文版：[README.zh-TW.md](README.zh-TW.md)

# MIRA — My Intelligent Research Assistant

A personal AI research assistant chatbot built with Django, Chainlit, and Groq LLM, featuring a RAG (Retrieval-Augmented Generation) pipeline for querying academic PDF documents, real-time web search via Tavily, and an optional safety guardrail layer powered by NeMo Guardrails.

---

## Features

- **Conversational AI** — Chat interface powered by Groq's `llama-3.3-70b-versatile` with multi-turn conversation history
- **RAG Knowledge Base** — Upload academic PDFs and query them with semantic search; the assistant answers based on retrieved content
- **Web Search** — Toggle real-time web search via Tavily; results are injected into the prompt as context before calling the LLM
- **Safety Guardrails** — Optional NeMo Guardrails layer that filters harmful or off-topic input/output using LLM-based self-check; can be toggled on/off per request for demo purposes
- **Persistent Vector Store** — Chroma index is saved to disk on first run; subsequent startups load instantly without re-embedding
- **Toggleable Modes** — Users can switch between general chat, RAG, web search, and guardrails from the Chainlit UI
- **Modular Architecture** — LLM client, RAG pipeline, web search, guardrails, and API are cleanly separated into reusable modules

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Chainlit 2.x |
| Backend | Django 5.x |
| LLM | Groq API (`llama-3.3-70b-versatile`) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector Store | Chroma (LangChain) |
| PDF Parsing | LangChain `PyPDFLoader` |
| Web Search | Tavily API |
| Guardrails | NeMo Guardrails 0.9+ |

---

## Architecture

```
User (Chainlit UI)
    ↓  POST /api/v1/chat/  { use_guardrails, use_rag, use_websearch }
Django (views.py)
    │
    ├── [Guardrails ON]  check_input(user_message)
    │                        ↓ blocked → return refusal immediately (no LLM call)
    │                        ↓ allowed → continue
    │
    ├── [Web Search ON]  user message → SearchManager → Tavily API → top-k results
    │                                     ↓
    │                                results + question → prompt
    ├── [RAG ON]         user message → RAGManager → Chroma → top-k chunks
    │                                     ↓
    │                                chunks + question → prompt
    └── [default]        user message ──────────────────────────→ prompt
                                           ↓
                                      Groq LLM → reply
                                           ↓
    ├── [Guardrails ON]  check_output(reply) → blocked → return refusal
    │                                        → allowed → return reply
    └──────────────────────────────────────────────────→ return reply
```

Priority: **Web Search > RAG > General Chat**

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
│       ├── views.py     # Chat endpoint with RAG / web search integration
│       └── urls.py
├── mira_frontend/       # Chainlit frontend
│   └── app.py           # UI with RAG and web search toggle switches
├── modules/
│   ├── llm/
│   │   └── groq_client.py         # Groq API wrapper
│   ├── rag/
│   │   ├── document_processor.py  # PDF loading & chunking
│   │   ├── vector_store.py        # Chroma build / load
│   │   ├── retriever.py           # Semantic search & prompt builder
│   │   └── rag_manager.py         # Unified RAG entry point
│   ├── websearch/
│   │   └── search_manager.py      # Tavily search & prompt builder
│   └── guardrails/
│       ├── guard_manager.py       # NeMo Guardrails wrapper (check_input / check_output)
│       └── config/
│           ├── config.yml         # Model config (Groq via OpenAI-compatible API)
│           ├── prompts.yml        # Self-check prompts for input and output rails
│           └── rails.co           # Colang flows defining rail behaviour
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
TAVILY_API_KEY=your_tavily_api_key   # optional, only needed for web search
```

Get a free Tavily API key at [tavily.com](https://tavily.com).

> **Note on NeMo Guardrails:** `GROQ_API_KEY` is reused for guardrails. NeMo calls Groq through an OpenAI-compatible endpoint (`https://api.groq.com/openai/v1`), so no additional API key is needed. Guardrails are disabled gracefully if `nemoguardrails` is not installed.

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

**Mode priority**
Web search takes priority over RAG, which takes priority over general chat. Only one enrichment path runs per request, keeping the prompt clean.

**Conversation history vs enriched prompt**
The RAG/web-search-enriched prompt is sent to the LLM but only the original user message is stored in conversation history. This keeps the chat log clean and prevents stale context from accumulating across turns.

**Persist path**
`RAGManager` is initialised with `config.DATA_DIR / 'vector_store'` (an absolute path) so the Chroma index is always found regardless of which directory Django is started from.

**Module-level initialisation**
`GroqClient`, `RAGManager`, `SearchManager`, and `GuardManager` are instantiated once at module load time in `views.py`, not per request, to avoid reloading models on every message.

**Guardrails as an optional filter**
Guardrails are controlled by a `use_guardrails` boolean in the request body, consistent with `use_rag` and `use_websearch`. This makes it easy to toggle the safety layer on and off during demos without restarting the server. When disabled, the request path is identical to the non-guardrails flow with zero overhead.

**NeMo Guardrails + Groq integration**
NeMo Guardrails expects an OpenAI-compatible LLM. `GuardManager.__init__` sets `OPENAI_API_KEY` and `OPENAI_API_BASE` at startup so NeMo transparently calls Groq without any changes to the Colang config. The `config.yml` also embeds `base_url` directly so the `${GROQ_API_KEY}` substitution works in both code and config paths.

**NeMo `generate()` returns a dict in newer versions (bug encountered)**
`LLMRails.generate()` is typed as returning `str`, but in practice some versions return a `dict`. Calling `.startswith()` on a dict raises `AttributeError`. Fixed by adding a `_extract_text()` helper in `guard_manager.py` that coerces the response to a string before comparison:
```python
def _extract_text(response) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return response.get("content") or response.get("response") or str(response)
    return str(response)
```

---

## Roadmap

- [x] Conversational chat with Groq LLM
- [x] RAG knowledge base (LangChain + Chroma)
- [x] Web search integration (Tavily)
- [x] Safety guardrails (NeMo Guardrails, toggleable)
- [ ] Improve RAG chunk quality (chunk size tuning, semantic chunking)
- [ ] Vision understanding via Groq Vision
- [ ] Voice input via Groq Whisper
- [ ] Deployment
- [ ] Migrate backend to FastAPI for async LLM calls
