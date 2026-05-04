import os
from rag.pdf_loader import load_and_split_pdf
from rag.embedder import create_vectorstore, save_vectorstore, load_vectorstore

KB_FOLDER = "F:/Slt_chatbotnew/knowledge_base"
KB_INDEX  = "F:/Slt_chatbotnew/kb_faiss_index"


def build_knowledge_base(model="llama3.2"):
    if not os.path.exists(KB_FOLDER):
        os.makedirs(KB_FOLDER)
        raise FileNotFoundError(
            f"Knowledge base folder created at {KB_FOLDER}. "
            "Please add PDF files and try again."
        )

    pdf_files = [f for f in os.listdir(KB_FOLDER) if f.lower().endswith(".pdf")]
    if not pdf_files:
        raise ValueError(f"No PDF files found in {KB_FOLDER}. Please add PDFs first.")

    all_chunks = []
    for filename in pdf_files:
        path   = os.path.join(KB_FOLDER, filename)
        chunks = load_and_split_pdf(path)
        all_chunks.extend(chunks)
        print(f"[KB] Loaded: {filename} → {len(chunks)} chunks")

    print(f"[KB] Total chunks: {len(all_chunks)}")
    vs = create_vectorstore(all_chunks, model=model)
    save_vectorstore(vs, KB_INDEX)
    print("[KB] Knowledge base saved!")
    return vs


def load_knowledge_base(model="llama3.2"):
    if os.path.exists(KB_INDEX):
        try:
            vs = load_vectorstore(KB_INDEX)
            print("[KB] Knowledge base loaded from disk.")
            return vs
        except Exception as e:
            print(f"[KB] Failed to load knowledge base: {e}")
            return None
    print("[KB] No saved knowledge base found.")
    return None