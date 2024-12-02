import datetime
import random
import requests

from abc import ABC, abstractmethod
from typing import Dict

def datetime_from_millis(millis: int):
    return datetime.datetime.fromtimestamp(millis / 1000)

class MarketFetcher(ABC):
    def _result_from_data(self, data):
        probability = data.get('probability')
        close_date = datetime_from_millis(data.get("closeTime"))
        result = {
            "title": data.get("question"),
            "description": data.get("textDescription"),
            "id": data.get("id"),
            "creator": data.get("creatorName"),
            "probability": probability,
            "current_date": datetime.datetime.now(),
            "close_date": close_date,
            "comments": data.get("comments", []),
        }
        return result

    @abstractmethod
    def get_market_data(self, url: str) -> Dict:
        pass


NOW_MILLISECONDS = int(datetime.datetime.now().timestamp() * 1000)

MOCK_MARKET_DATA = [
    {
        "question": "Will AI surpass human intelligence by 2030?",
        "textDescription": "This market will resolve to YES if a widely recognized AI system demonstrably outperforms humans across a broad range of cognitive tasks by December 31, 2030.",
        "id": "1",
        "creator": "Bob",
        "probability": 0.7,
        "current_date": NOW_MILLISECONDS,
        "close_date": NOW_MILLISECONDS,
        "comments": [
            {"user": "Alice", "text": "I think this is unlikely given current progress.",
                    "time": NOW_MILLISECONDS},
            {"user": "Bob", "text": "Recent advancements in language models suggest this might happen sooner than we think.",
             "time": NOW_MILLISECONDS},
        ]
    },
    {
        "title": "Will SpaceX successfully land humans on Mars by 2028?",
        "textDescription": "This market resolves to YES if SpaceX lands at least one human safely on the surface of Mars before January 1, 2029.",
        "id": "2",
        "creator": "Charlie",
        "probability": 0.3,
        "current_date": NOW_MILLISECONDS,
        "close_date": NOW_MILLISECONDS,
        "comments": [
            {"userName": "Alice", "text": "There are still many technological hurdles to overcome.",
             "time": NOW_MILLISECONDS},
            {"userName": "Bob", "text": "SpaceX has been making rapid progress",
             "time": NOW_MILLISECONDS},
        ]
    }
]


class MockMarketFetcher(MarketFetcher):
    def get_market_data(self, market_url: str) -> Dict:
        data = random.choice(MOCK_MARKET_DATA)
        return self._result_from_data(data)


class HttpMarketFetcher(MarketFetcher):
    def _collect_comment_text(self, data, collected_texts):
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "text" and isinstance(value, str):
                    collected_texts.append(value)
                else:
                    self._collect_comment_text(value, collected_texts)
        elif isinstance(data, list):
            for item in data:
                self._collect_comment_text(item, collected_texts)

    def _get_comments_data(self, slug: str):
        comments_response = requests.get(
            f"https://api.manifold.markets/v0/comments",
            params={"contractSlug": slug, "limit": 1000}
        )
        comments_response.raise_for_status()
        comments_data = comments_response.json()
        result = []
        # Order in reverse, to appear from earliest to latest.
        for comment_data in reversed(comments_data):
            collected_texts = []
            self._collect_comment_text(comment_data, collected_texts)
            comment_data["text"] = r"\n".join(collected_texts)
            # If the text is empty (maybe the comment had non-text content), ignore it.
            if not comment_data["text"]:
                continue
            comment_data["user"] = comment_data["userName"]
            comment_data["time"] = datetime_from_millis(comment_data["createdTime"]).strftime('%Y-%m-%d')
            result.append(comment_data)
        return result

    def get_market_data(self, market_url: str) -> Dict:
        slug = market_url.split('/')[-1]

        market_response = requests.get(
            f"https://api.manifold.markets/v0/slug/{slug}")
        market_response.raise_for_status()
        market_data = market_response.json()

        market_data["comments"] = self._get_comments_data(slug)

        return self._result_from_data(market_data)
