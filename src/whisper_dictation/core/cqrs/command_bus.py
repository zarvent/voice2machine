from typing import Dict, Type, Any
from .command import Command
from .command_handler import CommandHandler

class CommandBus:
    """Dispatches commands to their respective handlers."""

    def __init__(self) -> None:
        self.handlers: Dict[Type[Command], CommandHandler] = {}

    def register(self, handler: CommandHandler) -> None:
        """Registers a command handler."""
        command_type = handler.listen_to()
        if command_type in self.handlers:
            raise ValueError(f"Command handler already registered for {command_type}")
        self.handlers[command_type] = handler

    def dispatch(self, command: Command) -> Any:
        """Dispatches a command to its handler."""
        command_type = type(command)
        if command_type not in self.handlers:
            raise ValueError(f"No command handler registered for {command_type}")
        return self.handlers[command_type].handle(command)
