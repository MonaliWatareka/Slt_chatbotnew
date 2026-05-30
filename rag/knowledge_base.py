import os
from rag.pdf_loader import load_and_split_pdf
from rag.embedder   import create_vectorstore, save_vectorstore, load_vectorstore

KB_FOLDER = "F:/Slt_chatbotnew/knowledge_base"
KB_INDEX  = "F:/Slt_chatbotnew/kb_faiss_index"

def build_knowledge_base(model="llama3.2"):
    if not os.path.exists(KB_FOLDER):
        os.makedirs(KB_FOLDER)
        raise FileNotFoundError(f"Add SLT PDFs to {KB_FOLDER} and try again.")

    pdf_files = [f for f in os.listdir(KB_FOLDER) if f.lower().endswith(".pdf")]
    if not pdf_files:
        raise ValueError(f"No PDFs found in {KB_FOLDER}.")

    all_chunks = []
    for filename in pdf_files:
        chunks = load_and_split_pdf(os.path.join(KB_FOLDER, filename))
        all_chunks.extend(chunks)
        print(f"[KB] {filename} → {len(chunks)} chunks")

    vs = create_vectorstore(all_chunks, model=model)
    save_vectorstore(vs, KB_INDEX)
    return vs

def load_knowledge_base(model="llama3.2"):
    if os.path.exists(KB_INDEX):
        try:
            return load_vectorstore(KB_INDEX)
        except Exception as e:
            print(f"[KB] Load error: {e}")
    return None
