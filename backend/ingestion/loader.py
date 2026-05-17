from pathlib import Path
from langchain_community.document_loaders import (
    UnstructuredMarkdownLoader,
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)

SUPPORTED = {".md": UnstructuredMarkdownLoader, ".pdf": PyPDFLoader,
             ".docx": Docx2txtLoader, ".txt": TextLoader}

def load_document(file_path: str, tag: str) -> list:
    """Load a file and attach tag metadata to every chunk."""
    path = Path(file_path)
    loader_cls = SUPPORTED.get(path.suffix.lower())
    if not loader_cls:
        raise ValueError(f"Unsupported file type: {path.suffix}")
    
    docs = loader_cls(str(path)).load()
    for doc in docs:
        doc.metadata["tag"] = tag
        doc.metadata["filename"] = path.name
    return docs