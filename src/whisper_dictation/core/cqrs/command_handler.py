from abc import ABC, abstractmethod
from typing import Type
from .command import Command

class CommandHandler(ABC):
    """Base class for command handlers."""

    @abstractmethod
    def handle(self, command: Command) -> None:
        """Handles a command."""
        raise NotImplementedError

    def listen_to(self) -> Type[Command]:
        """Returns the type of command this handler listens to."""
        raise NotImplementedError
