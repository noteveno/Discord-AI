"""
Web Search Module using DuckDuckGo
Free, no-key API for real-time knowledge
"""
import logging
import asyncio
from typing import List, Dict, Any
from ddgs import DDGS

logger = logging.getLogger('Search')

class SearchEngine:
    """Handles web search requests"""
    
    @staticmethod
    async def search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Perform a web search
        """
        try:
            results = []
            
            # Run in executor to avoid blocking
            def _search():
                with DDGS() as ddgs:
                    # Use text search
                    search_results = list(ddgs.text(query, max_results=max_results))
                    return search_results
            
            search_results = await asyncio.to_thread(_search)
            
            for r in search_results:
                results.append({
                    "title": r.get("title", "No Title"),
                    "link": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
                
            logger.info(f"Found {len(results)} results for: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            return []
