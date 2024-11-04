import datetime
import random
import requests

from abc import ABC, abstractmethod
from typing import Dict

class MarketFetcher(ABC):
    def _result_from_data(self, data):
        probability = f"{100 * data.get('probability'):0.2f}%"
        close_date = datetime.datetime.fromtimestamp(data.get("closeTime") / 1000)
        result = {
                "title": data.get("question"),
                "description": data.get("textDescription"),
                "id": data.get("id"),
                "creator": data.get("creatorName"),
                "probability": probability,
                "current_date": datetime.datetime.now(),
                "close_date": close_date,
                "comments": [{"user": comment["user"], "text": comment["text"], "time": datetime.datetime.now()} for comment in data.get("comments", [])],  # Update
                }
        return result

    @abstractmethod
    def get_market_data(self, url: str) -> Dict:
        pass


MOCK_MARKET_DATA = [
        {
            "question": "Will AI surpass human intelligence by 2030?",
            "textDescription": "This market will resolve to YES if a widely recognized AI system demonstrably outperforms humans across a broad range of cognitive tasks by December 31, 2030.",
            "id": "1",
            "creator": "Bob",
            "probability": 0.7,
            "current_date": datetime.datetime.now(),
            "close_date": datetime.datetime.now(),
            "comments": [
                { "user": "Alice", "text": "I think this is unlikely given current progress.", "time": datetime.datetime.now() },
                { "user": "Bob", "text": "Recent advancements in language models suggest this might happen sooner than we think.", "time": datetime.datetime.now() },
                ]
            },
        {
            "title": "Will SpaceX successfully land humans on Mars by 2028?",
            "textDescription": "This market resolves to YES if SpaceX lands at least one human safely on the surface of Mars before January 1, 2029.",
            "id": "2",
            "creator": "Charlie",
            "probability": 0.3,
            "current_date": datetime.datetime.now(),
            "close_date": datetime.datetime.now(),
            "comments": [
                { "user": "Alice", "text": "There are still many technological hurdles to overcome.", "time": datetime.datetime.now() },
                { "user": "Bob", "text": "SpaceX has been making rapid progress", "time": datetime.datetime.now() },
                ]
            }
        ]


class MockMarketFetcher(MarketFetcher):
    def get_market_data(self, market_url: str) -> Dict:
        data = random.choice(MOCK_MARKET_DATA)
        return self._result_from_data(data)


class HttpMarketFetcher(MarketFetcher):
    def get_market_data(self, market_url: str) -> Dict:
        slug = market_url.split('/')[-1]
        response = requests.get(f"https://api.manifold.markets/v0/slug/{slug}")
        response.raise_for_status()
        data = response.json()
        return self._result_from_data(data)

