from abc import ABC, abstractmethod
import json
import random
from typing import Dict

class DecisionMaker(ABC):
    @abstractmethod
    def make_decision(self, context: str) -> Dict:
        pass

class RandomDecisionMaker(DecisionMaker):
    def make_decision(self, context: str) -> Dict:
        choices = ["BUY_YES", "BUY_NO", "DO_NOTHING"]
        result = {
                "choice": random.choice(choices),
                "reasoning": f"Reasoning for: {json.dumps(context)}"
                }
        return result

class YourDecisionMaker(DecisionMaker):
    def make_decision(self, context: str) -> Dict:
        raise NotImplementedError("You should implement this!")

