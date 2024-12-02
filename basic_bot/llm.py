from abc import ABC, abstractmethod
from typing import Dict, Any

import anthropic
import json
import os


class Llm(ABC):
    @abstractmethod
    def sample_text(self, prompt: str) -> str:
        """
        Returns a string response to the provided prompt.

        :param prompt: The input prompt to which the LLM will respond.
        :return: The LLM's response as a string.
        """
        pass

class MockLlm(Llm):
    def sample_text(self, prompt: str) -> str:
        return f"MOCK LLM<{prompt}>MOCK LLM"

class ClaudeLlm(Llm):
    def __init__(self, api_key, model):
        os.environ['ANTHROPIC_API_KEY'] = api_key
        self.model = model

    def sample_text(self, prompt: str, max_tokens=4096) -> str:
        response = anthropic.Anthropic().messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        assert len(response.content) == 1
        return response.content[0].text
