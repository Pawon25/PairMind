from ingestion.opensearch_store import get_client, INDEX_NAME
from ingestion.embedder import embed_texts

def hybrid_retrieve(query: str, tag_filter: list[str], top_k: int = 5) -> list[dict]:
    client = get_client()
    query_vec = embed_texts([query])[0]

    # Dense (kNN)
    knn_resp = client.search(index=INDEX_NAME, body={
        "size": top_k,
        "query": {"knn": {"embedding": {"vector": query_vec, "k": top_k}}},
        "post_filter": {"terms": {"tag": tag_filter}}
    })

    # BM25
    bm25_resp = client.search(index=INDEX_NAME, body={
        "size": top_k,
        "query": {
            "bool": {
                "must":   {"match": {"text": query}},
                "filter": {"terms": {"tag": tag_filter}}
            }
        }
    })

    # Reciprocal Rank Fusion
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}

    for rank, hit in enumerate(knn_resp["hits"]["hits"]):
        cid = hit["_id"]
        scores[cid] = scores.get(cid, 0) + 1 / (rank + 60)
        docs[cid] = hit["_source"]

    for rank, hit in enumerate(bm25_resp["hits"]["hits"]):
        cid = hit["_id"]
        scores[cid] = scores.get(cid, 0) + 1 / (rank + 60)
        docs[cid] = hit["_source"]

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [docs[cid] for cid, _ in ranked[:top_k]]


def buyer_retrieve(query: str) -> list[dict]:
    return hybrid_retrieve(query, tag_filter=["buyer-private", "shared"])

def seller_retrieve(query: str) -> list[dict]:
    return hybrid_retrieve(query, tag_filter=["seller-private", "shared"])