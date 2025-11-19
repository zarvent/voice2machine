"""
módulo que implementa el bus de comandos (command bus)

el command bus es el orquestador central del patrón CQRS en esta aplicación
su responsabilidad es recibir comandos y despacharlos al handler apropiado
que ha sido previamente registrado para manejarlos

este patrón desacopla al emisor de un comando (ej la CLI en `main.py`) del
receptor (el `commandhandler` que contiene la lógica de negocio)
"""

from typing import Dict, Type, Any
from .command import Command
from .command_handler import CommandHandler

class CommandBus:
    """
    despacha comandos a sus respectivos handlers

    actúa como un mediador que mapea un tipo de comando a la instancia del
    handler que puede procesarlo
    """

    def __init__(self) -> None:
        """
        inicializa el command bus

        crea un diccionario interno para mantener el registro de los handlers
        """
        self.handlers: Dict[Type[Command], CommandHandler] = {}

    def register(self, handler: CommandHandler) -> None:
        """
        registra un manejador de comandos

        durante la inicialización de la aplicación (en el contenedor de DI)
        este método es llamado para registrar cada handler disponible

        args:
            handler: la instancia del handler a registrar

        raises:
            valueerror: si ya existe un handler registrado para el mismo tipo de comando
        """
        command_type = handler.listen_to()
        if command_type in self.handlers:
            raise ValueError(f"Ya existe un handler registrado para el comando {command_type}")
        self.handlers[command_type] = handler

    async def dispatch(self, command: Command) -> Any:
        """
        despacha un comando a su handler correspondiente

        este es el método principal que se utiliza en tiempo de ejecución busca el
        handler apropiado para el comando dado y le delega la ejecución

        args:
            command: la instancia del comando a despachar

        returns:
            el resultado de la ejecución del método `handle` del handler

        raises:
            valueerror: si no se encuentra ningún handler registrado para el tipo de comando
        """
        command_type = type(command)
        if command_type not in self.handlers:
            raise ValueError(f"No hay un handler registrado para el comando {command_type}")
        return await self.handlers[command_type].handle(command)
