> 繁體中文版：[README.zh-TW.md](README.zh-TW.md)

# MIRA — My Intelligent Research Assistant

[![CI](https://github.com/wendywtchang/mira/actions/workflows/ci.yml/badge.svg)](https://github.com/wendywtchang/mira/actions/workflows/ci.yml)

A personal AI research assistant built with Django, Chainlit, and Groq LLM. Features two routing modes, a RAG pipeline for academic PDFs, real-time web search, and an optional safety guardrail layer.

---

## Features

- **Agentic Mode** — LLM decides which tool to call via function calling; routing decision is shown as a collapsible step in the UI for transparency
- **Manual Mode** — User explicitly toggles RAG, web search, or general chat; deterministic and fully predictable
- **RAG Knowledge Base** — Upload academic PDFs and query them with semantic search via Chroma + LangChain
- **Web Search** — Real-time search via Tavily API, injected as context before the LLM call
- **Safety Guardrails** — Optional NeMo Guardrails layer for input/output filtering; toggled per request with zero overhead when off
- **Persistent Vector Store** — Chroma index saved to disk; loads instantly on subsequent startups
- **Modular Architecture** — Each capability (LLM, RAG, search, guardrails, agent) is a standalone module

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Chainlit 2.x |
| Backend | Django 5.x |
| LLM (chat) | Groq API (`openai/gpt-oss-120b`) |
| LLM (tool use) | Groq API (`qwen/qwen3.6-27b`, fallback `openai/gpt-oss-120b`) |
| Function Calling | Groq native tool use (two-step dispatch) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector Store | Chroma (LangChain) |
| PDF Parsing | LangChain `PyPDFLoader` |
| Web Search | Tavily API |
| Guardrails | NeMo Guardrails 0.9+ |

---

## Architecture

```
User (Chainlit UI)
    ↓  POST /api/v1/chat/  { use_agentic, use_guardrails, use_rag, use_websearch }
Django (views.py)
    │
    ├── [Guardrails ON]  check_input(user_message)
    │                        ↓ blocked → return refusal (no LLM call)
    │
    ├── [Agentic Mode]   AgentManager.dispatch()
    │                        ↓ 1st call: LLM selects tool via function calling
    │                        ↓ execute tool (RAG or web search)
    │                        ↓ 2nd call: LLM synthesises final answer
    │
    └── [Manual Mode]    user-toggled routing (web search > RAG > general chat)
                                               ↓
                                          Groq LLM → reply
    │
    └── [Guardrails ON]  check_output(reply)
```

Both modes return `mode`, `tool_used`, and `query_used` so the Chainlit UI can display a routing decision step for comparison.

**RAG Pipeline:**
```
PDF → PyPDFLoader → RecursiveCharacterTextSplitter (chunk 500, overlap 50)
    → HuggingFaceEmbeddings → Chroma (data/vector_store/)
    → similarity_search() → context-injected prompt
```

---

## Project Structure

```
MIRA/
├── mira_backend/        # Django backend
│   └── api/
│       ├── views.py     # Chat endpoint — manual and agentic routing
│       └── urls.py
├── mira_frontend/       # Chainlit frontend
│   └── app.py           # Mode toggles + routing decision Step display
├── modules/
│   ├── llm/
│   │   └── groq_client.py         # Groq API wrapper (chat + tool use with fallback)
│   ├── agent/
│   │   └── agent_manager.py       # Two-step function calling dispatch
│   ├── rag/
│   │   ├── document_processor.py  # PDF loading & chunking
│   │   ├── vector_store.py        # Chroma build / load
│   │   ├── retriever.py           # Semantic search & prompt builder
│   │   └── rag_manager.py         # Unified RAG entry point
│   ├── websearch/
│   │   └── search_manager.py      # Tavily search & prompt builder
│   └── guardrails/
│       ├── guard_manager.py       # NeMo Guardrails wrapper
│       └── config/                # Colang rails config
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

### 3. Run

```bash
conda activate mira
python run_mira.py
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:8501`

### 4. Load the knowledge base

Place PDF files in `data/documents/`, then run once:

```python
from modules.rag import RAGManager
rag = RAGManager()
rag.load_documents(["data/documents/your_paper.pdf"])
```

The index persists to disk and is loaded automatically on subsequent startups.

---

## Key Design Decisions

**Agentic vs Manual mode**
Manual mode is deterministic — the user controls which tool runs. Agentic mode delegates that decision to the LLM via function calling. Both are available simultaneously so behaviour can be compared directly in the UI.

**Two-step function calling**
`AgentManager.dispatch()` makes two Groq API calls: the first lets the LLM pick a tool; the second feeds the tool result back and gets the final answer. The assistant's `tool_calls` message must be included in the second call or the API returns 400.

**Separate model for tool use**
`qwen/qwen3.6-27b` is used for tool-calling requests because it is fine-tuned for structured JSON output and has more generous free-tier rate limits than larger models. `openai/gpt-oss-120b` is used for general chat and as the tool-use fallback. `temperature=0` is set for all tool-use calls to minimise malformed output.

**Conversation history vs enriched prompt**
RAG/web-search context is injected into the prompt sent to the LLM, but only the original user message is stored in history. This keeps the chat log clean across turns.

**Module-level initialisation**
All managers (`GroqClient`, `RAGManager`, `SearchManager`, `GuardManager`, `AgentManager`) are instantiated once at Django module load time, not per request.

---

## Roadmap

- [x] Conversational chat with Groq LLM
- [x] RAG knowledge base (LangChain + Chroma)
- [x] Web search integration (Tavily)
- [x] Safety guardrails (NeMo Guardrails, toggleable)
- [x] Agentic mode with LLM function calling
- [x] Manual vs Agentic routing comparison UI
- [ ] Migrate tests to pytest
- [ ] CI/CD pipeline (GitHub Actions + deployment)
- [ ] Improve RAG chunk quality (semantic chunking)
- [ ] Voice input via Groq Whisper
- [ ] Vision understanding via Groq Vision
- [ ] Migrate backend to FastAPI for async LLM calls
