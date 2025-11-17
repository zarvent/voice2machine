"""
Módulo que define la interfaz para los manejadores de comandos (Command Handlers).

Un Command Handler es el componente que contiene la lógica de negocio para
procesar un comando específico. Cada handler se suscribe a un tipo de comando
y es invocado por el `CommandBus` cuando un comando de ese tipo es despachado.
"""

from abc import ABC, abstractmethod
from typing import Type
from .command import Command

class CommandHandler(ABC):
    """
    Clase base abstracta para los manejadores de comandos.

    Todos los handlers de la aplicación deben heredar de esta clase e implementar
    los métodos `handle` y `listen_to`.
    """

    @abstractmethod
    def handle(self, command: Command) -> None:
        """
        Contiene la lógica de negocio para procesar el comando.

        Este método es invocado por el `CommandBus`.

        Args:
            command: La instancia del comando a procesar.
        """
        raise NotImplementedError

    def listen_to(self) -> Type[Command]:
        """
        Especifica a qué tipo de comando se suscribe este handler.

        El `CommandBus` utiliza este método para registrar el handler y saber
        a cuál invocar para un comando dado.

        Returns:
            El tipo de la clase del comando (ej. `StartRecordingCommand`).
        """
        raise NotImplementedError
