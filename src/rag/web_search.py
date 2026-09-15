from ddgs import DDGS
from loguru import logger


class DuckDuckGoSearchTool:
    """Wrapper for DuckDuckGo search."""

    def __init__(self, max_results: int = 3) -> None:
        self._max_results = max_results

    def search(self, query: str) -> str:
        """Perform a web search. Returns concatenated results text."""
        try:
            logger.debug("Web search: {}", query)
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=self._max_results))
            if not results:
                logger.debug("No web search results for: {}", query)
                return ""
            text_parts = [r.get("body", "") for r in results if r.get("body")]
            combined = "\n\n".join(text_parts)
            logger.debug("Web search returned {} results ({} chars)", len(results), len(combined))
            return combined
        except Exception as e:
            logger.error("Web search failed: {}", e)
            return ""
