from abc import ABC, abstractmethod

class ClipboardInterface(ABC):
    @abstractmethod
    def copy(self, text: str) -> None:
        """copia el texto al portapapeles"""
        pass

    @abstractmethod
    def paste(self) -> str:
        """pega el texto del portapapeles"""
        pass

class NotificationInterface(ABC):
    @abstractmethod
    def notify(self, title: str, message: str) -> None:
        """envía una notificación al sistema"""
        pass
