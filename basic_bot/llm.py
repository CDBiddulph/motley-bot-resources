from abc import ABC, abstractmethod
from typing import Dict, Any

class Llm(ABC):
    @abstractmethod
    def sample_text(self, prompt: str) -> str:
        """
        Returns a string response to the provided prompt.

        :param prompt: The input prompt to which the LLM will respond.
        :return: The LLM's response as a string.
        """
        pass

    @abstractmethod
    def sample_json(self, prompt: str) -> Dict[str, Any]:
        pass

class MockLlm(Llm):
    def sample_text(self, prompt: str) -> str:
        return f"MOCK LLM<{prompt}>MOCK LLM"

    def sample_json(self, prompt: str) -> Dict[str, Any]:
        return {"prompt": prompt}

class GptLlm(Llm):
    def sample_text(self, prompt: str) -> str:
        raise UnimplementedError()

    def sample_json(self, prompt: str) -> Dict[str, Any]:
        raise UnimplementedError()
