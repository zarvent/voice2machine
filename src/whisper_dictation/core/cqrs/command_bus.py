"""
Módulo que implementa el Bus de Comandos (Command Bus).

El Command Bus es el orquestador central del patrón CQRS en esta aplicación.
Su responsabilidad es recibir comandos y despacharlos al handler apropiado
que ha sido previamente registrado para manejarlos.

Este patrón desacopla al emisor de un comando (ej. la CLI en `main.py`) del
receptor (el `CommandHandler` que contiene la lógica de negocio).
"""

from typing import Dict, Type, Any
from .command import Command
from .command_handler import CommandHandler

class CommandBus:
    """
    Despacha comandos a sus respectivos handlers.

    Actúa como un mediador que mapea un tipo de comando a la instancia del
    handler que puede procesarlo.
    """

    def __init__(self) -> None:
        """
        Inicializa el Command Bus.

        Crea un diccionario interno para mantener el registro de los handlers.
        """
        self.handlers: Dict[Type[Command], CommandHandler] = {}

    def register(self, handler: CommandHandler) -> None:
        """
        Registra un manejador de comandos.

        Durante la inicialización de la aplicación (en el contenedor de DI),
        este método es llamado para registrar cada handler disponible.

        Args:
            handler: La instancia del handler a registrar.

        Raises:
            ValueError: Si ya existe un handler registrado para el mismo tipo de comando.
        """
        command_type = handler.listen_to()
        if command_type in self.handlers:
            raise ValueError(f"Ya existe un handler registrado para el comando {command_type}")
        self.handlers[command_type] = handler

    async def dispatch(self, command: Command) -> Any:
        """
        Despacha un comando a su handler correspondiente.

        Este es el método principal que se utiliza en tiempo de ejecución. Busca el
        handler apropiado para el comando dado y le delega la ejecución.

        Args:
            command: La instancia del comando a despachar.

        Returns:
            El resultado de la ejecución del método `handle` del handler.

        Raises:
            ValueError: Si no se encuentra ningún handler registrado para el tipo de comando.
        """
        command_type = type(command)
        if command_type not in self.handlers:
            raise ValueError(f"No hay un handler registrado para el comando {command_type}")
        return await self.handlers[command_type].handle(command)
