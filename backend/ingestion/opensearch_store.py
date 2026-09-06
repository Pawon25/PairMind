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
        # Existing index predates the session_id field — add it non-destructively
        # (adding a new field to a mapping is safe; changing an existing one isn't).
        client.indices.put_mapping(index=INDEX_NAME, body={
            "properties": {"session_id": {"type": "keyword"}}
        })
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
                "text":       {"type": "text"},
                "filename":   {"type": "keyword"},
                "tag":        {"type": "keyword"},
                "chunk_id":   {"type": "keyword"},
                "section":    {"type": "keyword"},
                "session_id": {"type": "keyword"},
            }
        }
    })

def _chunk_id(text: str, filename: str, session_id: str) -> str:
    return hashlib.md5(f"{session_id}:{filename}:{text}".encode()).hexdigest()

def upsert_chunks(chunks: list, embeddings: list[list[float]], session_id: str):
    client = get_client()
    for chunk, embedding in zip(chunks, embeddings):
        cid = _chunk_id(chunk.page_content, chunk.metadata["filename"], session_id)
        # Skip if already indexed (embedding cache) - scoped per session_id above,
        # so this never skips indexing for a different visitor's identical content.
        if client.exists(index=INDEX_NAME, id=cid):
            continue
        client.index(index=INDEX_NAME, id=cid, body={
            "chunk_id":   cid,
            "text":       chunk.page_content,
            "filename":   chunk.metadata["filename"],
            "tag":        chunk.metadata["tag"],
            "section":    chunk.metadata.get("section", ""),
            "embedding":  embedding,
            "session_id": session_id,
        })

def delete_session_chunks(session_id: str):
    """Scoped reset — deletes only this session's indexed chunks, not the shared index."""
    client = get_client()
    if not client.indices.exists(index=INDEX_NAME):
        return
    client.delete_by_query(index=INDEX_NAME, body={
        "query": {"term": {"session_id": session_id}}
    }, refresh=True)

# def fetch_citation_snippet(filename: str, section: str) -> str | None:
#     """Fetch the most relevant chunk for a given filename + section."""
#     client = get_client()
#     query = {
#         "query": {
#             "bool": {
#                 "must": [
#                     {"match": {"filename": filename}}
#                 ],
#                 "should": [
#                     {"match": {"section": section}},
#                     {"match": {"text": section}}
#                 ]
#             }
#         },
#         "size": 1
#     }
#     try:
#         res = client.search(index=INDEX_NAME, body=query)
#         hits = res["hits"]["hits"]
#         if hits:
#             return hits[0]["_source"]["text"]
#         return None
#     except Exception:
#         return None

# def fetch_citation_snippet(filename: str, section: str) -> str | None:
#     client = get_client()
#     query = {
#         "query": {
#             "bool": {
#                 "must": [
#                     {"term": {"filename": filename}}
#                 ],
#                 "should": [
#                     {"match_phrase": {"text": section}},
#                     {"match": {"text": section}}
#                 ],
#                 "minimum_should_match": 0
#             }
#         },
#         "_source": ["text"],
#         "size": 1
#     }
#     try:
#         res = client.search(index=INDEX_NAME, body=query)
#         hits = res["hits"]["hits"]
#         if hits:
#             return hits[0]["_source"]["text"]
#         return None
#     except Exception:
#         return None

def fetch_citation_snippet(filename: str, section: str) -> str | None:
    client = get_client()

    # Map section references to keywords likely in that section's text
    section_keywords = {
        "1": "budget ceiling",
        "2": "market benchmark",
        "3": "payment terms",
        "4": "delivery",
        "5": "walk-away",
        "6": "fallback",
    }

    # Extract section number from strings like "Section 1", "Section 2. Market..."
    import re
    sec_num = None
    match = re.search(r'section\s*(\d+)', section, re.IGNORECASE)
    if match:
        sec_num = match.group(1)

    keyword = section_keywords.get(sec_num, section) if sec_num else section

    query = {
        "query": {
            "bool": {
                "must": [{"term": {"filename": filename}}],
                "should": [
                    {"match_phrase": {"text": keyword}},
                    {"match": {"text": keyword}},
                ],
                "minimum_should_match": 1
            }
        },
        "highlight": {
            "fields": {"text": {}},
            "fragment_size": 400,
            "number_of_fragments": 1
        },
        "_source": ["text"],
        "size": 1
    }
    try:
        res = client.search(index=INDEX_NAME, body=query)
        hits = res["hits"]["hits"]
        if not hits:
            return None
        highlight = hits[0].get("highlight", {}).get("text", [])
        if highlight:
            return highlight[0]
        return hits[0]["_source"]["text"][:500]
    except Exception:
        return None