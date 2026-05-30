from functools import lru_cache
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS

EMBED_MODEL = "nomic-embed-text"

@lru_cache(maxsize=1)
def _get_embeddings():
    return OllamaEmbeddings(model=EMBED_MODEL)

def create_vectorstore(chunks, model: str = "llama3.2"):
    embeddings  = _get_embeddings()
    print(f"[embedder] Embedding {len(chunks)} chunks...")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    print("[embedder] FAISS index built.")
    return vectorstore

def save_vectorstore(vectorstore, path: str = "faiss_index"):
    vectorstore.save_local(path)
    print(f"[embedder] Saved vectorstore to: {path}")

def load_vectorstore(path: str = "faiss_index"):
    embeddings = _get_embeddings()
    return FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
