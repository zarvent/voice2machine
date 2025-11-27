"""
modulo que implementa el bus de comandos (command bus).

el command bus es el orquestador central del patron cqrs en esta aplicacion.
su responsabilidad es recibir comandos y despacharlos al handler apropiado
que ha sido previamente registrado para manejarlos.

este patron desacopla al emisor de un comando (ej la cli en `main.py`) del
receptor (el `commandhandler` que contiene la logica de negocio).
"""

from typing import Dict, Type, Any
from .command import Command
from .command_handler import CommandHandler

class CommandBus:
    """
    despacha comandos a sus respectivos handlers.

    actua como un mediador que mapea un tipo de comando a la instancia del
    handler que puede procesarlo.
    """

    def __init__(self) -> None:
        """
        inicializa el command bus.

        crea un diccionario interno para mantener el registro de los handlers.
        """
        self.handlers: Dict[Type[Command], CommandHandler] = {}

    def register(self, handler: CommandHandler) -> None:
        """
        registra un manejador de comandos.

        durante la inicializacion de la aplicacion (en el contenedor de di),
        este metodo es llamado para registrar cada handler disponible.

        args:
            handler (CommandHandler): la instancia del handler a registrar.

        raises:
            ValueError: si ya existe un handler registrado para el mismo tipo de comando.
        """
        command_type = handler.listen_to()
        if command_type in self.handlers:
            raise ValueError(f"Ya existe un handler registrado para el comando {command_type}")
        self.handlers[command_type] = handler

    async def dispatch(self, command: Command) -> Any:
        """
        despacha un comando a su handler correspondiente.

        este es el metodo principal que se utiliza en tiempo de ejecucion. busca el
        handler apropiado para el comando dado y le delega la ejecucion.

        args:
            command (Command): la instancia del comando a despachar.

        returns:
            Any: el resultado de la ejecucion del metodo `handle` del handler.

        raises:
            ValueError: si no se encuentra ningun handler registrado para el tipo de comando.
        """
        command_type = type(command)
        if command_type not in self.handlers:
            raise ValueError(f"No hay un handler registrado para el comando {command_type}")
        return await self.handlers[command_type].handle(command)
