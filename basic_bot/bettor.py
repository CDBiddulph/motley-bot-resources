import requests
from abc import ABC, abstractmethod
from typing import Dict


class Bettor(ABC):
    @abstractmethod
    def bet(self, market_id: str, bet: str) -> None:
        pass


class HttpBettor(Bettor):
    def init(self, api_key, dry_run=False):
        self._api_key = api_key
        self._dry_run = dry_run

    def bet(self, market_id: str, bet: str) -> None:
        if bet == "DO_NOTHING":
            return
        elif bet == "BUY_YES":
            outcome = "YES"
        elif bet == "BUY_NO":
            outcome = "NO"
        else:
            raise ValueError(f"Invalid bet: {bet}")

        response = requests.post(
            "https://api.manifold.markets/v0/bet",
            headers={
                'Authorization': f'Key {self._api_key}',
                'Content-Type': 'application/json'
            },
            json={
                "amount": 1,
                "contractId": market_id,
                "outcome": outcome,
                "dryRun": self._dry_run
            }
        )

        response.raise_for_status()
