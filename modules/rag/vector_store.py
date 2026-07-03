import os

from langchain_chroma import Chroma


class VectorStore:
    def __init__(self, persist_dir='data/vector_store', model_name='all-MiniLM-L6-v2'):
        self.model_name = model_name
        self._embeddings = None
        self.persist_dir = persist_dir
        self.db = None

    @property
    def embeddings(self):
        # lazy loading：embedding 模型（PyTorch，300MB+ RAM）只在真正需要時載入，
        # 部署環境沒有向量資料庫時完全不載入，free tier 512MB 才夠用
        if self._embeddings is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            self._embeddings = HuggingFaceEmbeddings(model_name=self.model_name)
        return self._embeddings

    def is_built(self):
        # 檢查磁碟上是否已有向量資料庫
        return os.path.exists(self.persist_dir) and len(os.listdir(self.persist_dir)) > 0

    def build(self, documents):
        # 從 LangChain Document 列表建立向量索引並自動持久化
        print(f"Building index and saving to {self.persist_dir} ...")
        self.db = Chroma.from_documents(
            documents,
            self.embeddings,
            persist_directory=self.persist_dir,
        )
        print(f"Index built: {self.db._collection.count()} chunks stored")

    def load(self):
        # 從磁碟載入已存在的向量索引（啟動時使用，不需重新 embedding）
        if not self.is_built():
            raise FileNotFoundError(
                f"找不到向量資料庫：{self.persist_dir}，請先執行 build()"
            )
        print(f"Loading index from {self.persist_dir} ...")
        self.db = Chroma(
            persist_directory=self.persist_dir,
            embedding_function=self.embeddings,
        )
        print(f"Index loaded: {self.db._collection.count()} chunks available")
