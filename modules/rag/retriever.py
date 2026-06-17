class Retriever:
    def __init__(self, vector_store):
        # 接收 VectorStore 實例，共用其 db
        self.vs = vector_store

    def _check_ready(self):
        if self.vs.db is None:
            raise RuntimeError("Index not loaded. Call build() or load() first.")

    def search(self, query, top_k=3):
        # 回傳最相關的 top_k 個 LangChain Document 物件
        self._check_ready()
        return self.vs.db.similarity_search(query, k=top_k)

    def get_prompt_with_context(self, question, top_k=3):
        # 將知識庫檢索結果注入問題，回傳完整 prompt 供 views.py 直接使用
        self._check_ready()
        docs = self.search(question, top_k)

        # 組合 context，每筆標注來源與頁碼
        context_parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('source', 'unknown')
            # PyPDFLoader 頁碼從 0 開始，+1 轉成人類習慣的頁碼
            page = doc.metadata.get('page', 0) + 1
            context_parts.append(
                f"[{i}] Source: {source} (page {page})\n{doc.page_content}"
            )

        context = "\n\n".join(context_parts)

        prompt = (
            f"The following are relevant excerpts from the knowledge base:\n\n"
            f"{context}\n\n"
            f"Based on the above, answer this question: {question}"
        )
        return prompt
