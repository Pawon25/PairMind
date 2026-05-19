import os
from datetime import date

def tavily_search(query: str) -> tuple[str, list[dict]]:
    """Returns (formatted_string, list of {url, retrieved_date})"""
    try:
        from tavily import TavilyClient
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "", []

        tavily = TavilyClient(api_key=api_key)
        response = tavily.search(query=query, max_results=3)

        results = []
        citations = []
        today = date.today().isoformat()
        for r in response.get("results", []):
            url = r.get("url", "")
            snippet = r.get("content", "")[:300]
            results.append(f"URL: {url}\nRetrieved: {today}\nSnippet: {snippet}")
            if url:
                citations.append({"url": url, "retrieved_date": today})

        return "\n\n".join(results), citations

    except Exception as e:
        print(f"[web_search] Tavily failed: {e}")
        return "", []