from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

HEADERS_TO_SPLIT = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]

md_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=HEADERS_TO_SPLIT,
    strip_headers=False,
)
char_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)


def chunk_documents(docs: list) -> list:
    """
    Split docs into chunks, preserving metadata.
    For markdown files: extract section headers and attach to each chunk.
    For other files: fall back to plain character splitting.
    """
    result = []

    for doc in docs:
        filename = doc.metadata.get("filename", "")
        is_markdown = filename.lower().endswith(".md")

        if is_markdown:
            try:
                md_chunks = md_splitter.split_text(doc.page_content)
                for chunk in md_chunks:
                    sub_chunks = char_splitter.split_documents([chunk])
                    for sc in sub_chunks:
                        # Preserve original doc metadata (tag, filename)
                        sc.metadata.update(doc.metadata)
                        # Best available header as section name
                        sc.metadata["section"] = (
                            chunk.metadata.get("h3")
                            or chunk.metadata.get("h2")
                            or chunk.metadata.get("h1")
                            or ""
                        )
                    result.extend(sub_chunks)
            except Exception:
                # Fallback: treat as plain text if markdown parsing fails
                chunks = char_splitter.split_documents([doc])
                for c in chunks:
                    c.metadata.setdefault("section", "")
                result.extend(chunks)
        else:
            chunks = char_splitter.split_documents([doc])
            for c in chunks:
                c.metadata.update(doc.metadata)
                c.metadata.setdefault("section", "")
            result.extend(chunks)

    return result