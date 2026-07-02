from .document_processor import load_pdfs
from .retriever import Retriever
from .vector_store import VectorStore


class RAGManager:
    def __init__(self, persist_dir='data/vector_store', model_name='all-MiniLM-L6-v2'):
        # 初始化向量資料庫和檢索器
        self.vector_store = VectorStore(persist_dir, model_name)
        self.retriever = Retriever(self.vector_store)

    def load_documents(self, pdf_paths, chunk_size=500, chunk_overlap=50):
        # 載入 PDF、建立向量索引並持久化至磁碟
        docs = load_pdfs(pdf_paths, chunk_size, chunk_overlap)
        self.vector_store.build(docs)

    def load(self):
        # 從磁碟載入已建立的向量索引（每次啟動 MIRA 時呼叫，跳過重新 embedding）
        self.vector_store.load()

    def is_built(self):
        # 檢查向量資料庫是否已存在
        return self.vector_store.is_built()

    def query(self, question, top_k=3):
        # 查詢知識庫，回傳 LangChain Document 列表
        return self.retriever.search(question, top_k)

    def get_prompt_with_context(self, question, top_k=3):
        # 回傳注入知識庫內容的完整 prompt，供 views.py 直接帶入 LLM
        return self.retriever.get_prompt_with_context(question, top_k)
