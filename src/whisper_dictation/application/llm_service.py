from abc import ABC, abstractmethod

class LLMService(ABC):
    """Abstract base class for language model services."""

    @abstractmethod
    def process_text(self, text: str) -> str:
        raise NotImplementedError
