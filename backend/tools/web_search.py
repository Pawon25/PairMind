import os
from datetime import date

def tavily_search(query: str) -> str:
    """
    Search the web via Tavily. Returns formatted string of results,
    or empty string on any failure (negotiation must continue regardless).
    """
    try:
        from tavily import TavilyClient
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return ""

        tavily = TavilyClient(api_key=api_key)
        response = tavily.search(query=query, max_results=3)

        results = []
        today = date.today().isoformat()
        for r in response.get("results", []):
            url = r.get("url", "")
            snippet = r.get("content", "")[:300]
            results.append(f"URL: {url}\nRetrieved: {today}\nSnippet: {snippet}")

        return "\n\n".join(results)

    except Exception as e:
        # Graceful failure — log but don't crash negotiation
        print(f"[web_search] Tavily failed: {e}")
        return ""