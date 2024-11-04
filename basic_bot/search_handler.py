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

    def search(self, query: str):
        response = requests.get(
                self._SEARCH_URL,
                headers={"Ocp-Apim-Subscription-Key": self._api_key},
                params={"q": query, "count": self._results_per_query}
                )
        response.raise_for_status()
        search_results = response.json()

        if 'webPages' not in search_results:
            return []
        return [snippet['snippet'] for snippet in search_results['webPages']['value']]
