from abc import ABC, abstractmethod

class ClipboardInterface(ABC):
    @abstractmethod
    def copy(self, text: str) -> None:
        """Copies text to the clipboard."""
        pass

    @abstractmethod
    def paste(self) -> str:
        """Pastes text from the clipboard."""
        pass

class NotificationInterface(ABC):
    @abstractmethod
    def notify(self, title: str, message: str) -> None:
        """Sends a system notification."""
        pass
