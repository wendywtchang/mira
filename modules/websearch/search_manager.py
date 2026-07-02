# modules/websearch/search_manager.py
from tavily import TavilyClient

import config


class SearchManager:
    def __init__(self):
        if not config.TAVILY_API_KEY:
            raise ValueError("TAVILY_API_KEY not found. Please add it to your .env file.")
        self.client = TavilyClient(api_key=config.TAVILY_API_KEY)

    def search(self, query, max_results=3):
        response = self.client.search(query, max_results=max_results)
        print(response)  # 先看一下完整結構
        return response['results']

    def get_prompt_with_context(self, query, max_results=3):
        results = self.search(query, max_results)
        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(f"[{i}] {r['title']}\n{r['content']}\nSource: {r['url']}")
        context = "\n\n".join(context_parts)
        return f"Here is the web search results：\n\n{context}\n\nPlease answer the query according to the search results：{query}"