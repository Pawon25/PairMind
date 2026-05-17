from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)

def chunk_documents(docs: list) -> list:
    """Split docs into chunks, preserving metadata."""
    return splitter.split_documents(docs)