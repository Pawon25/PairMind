import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from ingestion.loader import load_document
from ingestion.chunker import chunk_documents
from ingestion.embedder import embed_texts
from ingestion.opensearch_store import create_index_if_not_exists, upsert_chunks, get_client, INDEX_NAME

SAMPLE_DOCS = [
    ("../data/sample-docs/Meridian-Procurement-Memo_Buyer-Private.md", "buyer-private"),
    ("../data/sample-docs/RFQ-2026-MER-0847_Shared.md",                "shared"),
    ("../data/sample-docs/ScanTech-Pricing-Sheet_Seller-Private.md",    "seller-private"),
]

def run():
    print("1. Creating index...")
    create_index_if_not_exists()
    print("   ✓ Index ready")

    for path, tag in SAMPLE_DOCS:
        print(f"\n2. Loading: {path} [{tag}]")
        docs   = load_document(path, tag)
        chunks = chunk_documents(docs)
        print(f"   ✓ {len(chunks)} chunks")

        texts      = [c.page_content for c in chunks]
        embeddings = embed_texts(texts)
        print(f"   ✓ Embedded")

        upsert_chunks(chunks, embeddings)
        print(f"   ✓ Upserted to OpenSearch")

    # Verify
    print("\n3. Verifying...")
    client = get_client()
    res = client.count(index=INDEX_NAME)
    print(f"   ✓ Total chunks in OpenSearch: {res['count']}")

    # Test tag isolation
    buyer = client.count(index=INDEX_NAME, body={"query": {"terms": {"tag": ["buyer-private"]}}})
    seller = client.count(index=INDEX_NAME, body={"query": {"terms": {"tag": ["seller-private"]}}})
    shared = client.count(index=INDEX_NAME, body={"query": {"terms": {"tag": ["shared"]}}})
    print(f"   buyer-private: {buyer['count']} | seller-private: {seller['count']} | shared: {shared['count']}")

    print("\n✅ Phase 1 complete!")

if __name__ == "__main__":
    run()