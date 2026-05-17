import hashlib
import os
from opensearchpy import OpenSearch

OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
INDEX_NAME = "pairmind-docs"
EMBEDDING_DIM = 384

def get_client():
    return OpenSearch(
        hosts=[OPENSEARCH_URL],
        timeout=30,
        max_retries=3,
        retry_on_timeout=True
    )

def create_index_if_not_exists():
    client = get_client()
    if client.indices.exists(index=INDEX_NAME):
        return
    client.indices.create(index=INDEX_NAME, body={
        "settings": {"index": {"knn": True}},
        "mappings": {
            "properties": {
                "embedding": {
                    "type": "knn_vector",
                    "dimension": EMBEDDING_DIM,
                    "method": {"name": "hnsw", "engine": "lucene"}
                },
                "text":     {"type": "text"},
                "filename": {"type": "keyword"},
                "tag":      {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "section":  {"type": "keyword"},
            }
        }
    })

def _chunk_id(text: str, filename: str) -> str:
    return hashlib.md5(f"{filename}:{text}".encode()).hexdigest()

def upsert_chunks(chunks: list, embeddings: list[list[float]]):
    client = get_client()
    for chunk, embedding in zip(chunks, embeddings):
        cid = _chunk_id(chunk.page_content, chunk.metadata["filename"])
        # Skip if already indexed (embedding cache)
        if client.exists(index=INDEX_NAME, id=cid):
            continue
        client.index(index=INDEX_NAME, id=cid, body={
            "chunk_id": cid,
            "text":     chunk.page_content,
            "filename": chunk.metadata["filename"],
            "tag":      chunk.metadata["tag"],
            "section":  chunk.metadata.get("section", ""),
            "embedding": embedding,
        })