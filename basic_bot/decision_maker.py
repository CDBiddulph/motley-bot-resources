from abc import ABC, abstractmethod
import json
import random
import re
from typing import Dict
from llm import Llm


class DecisionMaker(ABC):
    @abstractmethod
    def make_decision(self, prompt: str, market_probability: float) -> Dict:
        pass


class RandomDecisionMaker(DecisionMaker):
    def make_decision(self, prompt: str, market_probability: float) -> Dict:
        choices = ["BUY_YES", "BUY_NO", "DO_NOTHING"]
        result = {
            "decision": random.choice(choices),
            "probability": random.random(),
            "reasoning": f"Reasoning for: {json.dumps(prompt)}"
        }
        return result


class LlmDecisionMaker(DecisionMaker):
    def __init__(self, llm: Llm):
        self.llm = llm

    def make_decision(self, prompt: str, market_probability: float) -> Dict:
        # Send the prompt to the LLM
        response_text = self.llm.sample_text(prompt)

        # This error should be populated if there is any error.
        # If this happens we will just print a warning and use DO_NOTHING.
        error_str = None

        # Extract the probability from the <answer></answer> tags
        regex = r'<answer>\s*\**\s*(.*?)\s*\**\s*</answer>'
        answer_match = re.search(regex, response_text, re.DOTALL)
        if answer_match:
            probability_str = answer_match.group(1).strip()
            try:
                probability = float(probability_str)
            except ValueError as e:
                probability = None
                error_str = str(e)
        else:
            probability = None
            error_str = f"Could not find a match for regex: {regex}"

        if probability is not None and not (0 <= probability <= 1):
            error_str = f"Probability {probability} is not in the range [0, 1]"
            probability = None

        # Decide the action based on the comparison
        if probability is None:
            decision = "DO_NOTHING"
        elif probability < market_probability:
            decision = "BUY_NO"
        elif probability > market_probability:
            decision = "BUY_YES"
        else:
            decision = "DO_NOTHING"

        result = {
            "decision": decision,
            "reasoning": response_text
        }
        if probability is not None:
            result["probability"] = probability
        if error_str is not None:
            result["error"] = error_str
            print(f"WARNING: in LlmDecisionMaker, got the error: {error_str}")
        return result
