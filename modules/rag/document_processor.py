from tqdm import tqdm


def load_pdfs(pdf_paths, chunk_size=500, chunk_overlap=50):
    # lazy import：langchain_community 在 import 時就會載入 torch（300MB+ RAM），
    # 但 load_pdfs 只有建索引時才用到，production 上不會執行
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    # 遍歷所有 PDF 檔案，逐一載入
    all_docs = []
    for pdf_path in tqdm(pdf_paths, desc="Loading PDFs"):
        loader = PyPDFLoader(pdf_path)
        # 每個 Document 對應一頁，metadata 含 source 和 page
        all_docs.extend(loader.load())

    print(f"Loaded {len(all_docs)} pages")

    # 將頁面切割成較小的 chunks（預設 500 字 / 50 字重疊）
    # 學術論文建議 chunk_size=500，保留足夠語意又不會超過 context 長度
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = splitter.split_documents(all_docs)

    print(f"Split into {len(chunks)} chunks")
    return chunks
