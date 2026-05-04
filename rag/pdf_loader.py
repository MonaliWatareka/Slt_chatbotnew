from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_and_split_pdf(pdf_path: str, chunk_size: int = 500, chunk_overlap: int = 60):
    loader   = PyMuPDFLoader(pdf_path)
    pages    = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size    = chunk_size,
        chunk_overlap = chunk_overlap,
        separators    = ["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(pages)
    # Tag chunks with source filename for attribution
    for chunk in chunks:
        chunk.metadata["source_file"] = pdf_path.split("/")[-1].split("\\")[-1]
    print(f"[pdf_loader] {len(pages)} pages → {len(chunks)} chunks")
    return chunks