from abc import ABC, abstractmethod
import requests


class SearchHandler(ABC):
    @abstractmethod
    def search(self, query: str) -> str:
        pass


class MockSearchHandler(SearchHandler):
    def search(self, query: str) -> str:
        return [f"Search result for: {query}"]


class BingSearchHandler(SearchHandler):
    _SEARCH_URL = "https://api.bing.microsoft.com/v7.0/search"

    def __init__(self, api_key, results_per_query: int = 5):
        self._api_key = api_key
        self._results_per_query = results_per_query

    def _format_snippet(self, snippet):
        result = snippet['snippet']
        date = snippet['datePublishedDisplayText'] if 'datePublishedDisplayText' in snippet else None
        if date is not None:
            result = f"{result} (Date published: {date})"
        return result


    def search(self, query: str):
        # The query might come in quotes, which will severely restrict search results.
        # Just remove all quotes from the string.
        query = query.replace('"', "").replace("'", "")
        response = requests.get(
            self._SEARCH_URL,
            headers={"Ocp-Apim-Subscription-Key": self._api_key},
            params={"q": query, "count": self._results_per_query}
        )
        response.raise_for_status()
        search_results = response.json()

        if 'webPages' not in search_results:
            return []
        return [
            self._format_snippet(snippet)
            for snippet in search_results['webPages']['value']
        ]
