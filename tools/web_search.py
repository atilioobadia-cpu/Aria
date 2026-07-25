from duckduckgo_search import DDGS
from utils.logger import setup_logger

log = setup_logger("aria.search")


def web_search(query, max_results=3):
    if not query or not query.strip():
        return "No query provided"
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return f"No results found for '{query}'"
        lines = []
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            lines.append(f"{title}: {body}")
        return "\n".join(lines)
    except Exception as e:
        log.error("Web search failed: %s", e)
        return f"Search failed: {e}"
