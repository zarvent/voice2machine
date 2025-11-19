"""
módulo que define la interfaz para los manejadores de comandos (command handlers)

un command handler es el componente que contiene la lógica de negocio para
procesar un comando específico cada handler se suscribe a un tipo de comando
y es invocado por el `commandbus` cuando un comando de ese tipo es despachado
"""

from abc import ABC, abstractmethod
from typing import Type
from .command import Command

class CommandHandler(ABC):
    """
    clase base abstracta para los manejadores de comandos

    todos los handlers de la aplicación deben heredar de esta clase e implementar
    los métodos `handle` y `listen_to`
    """

    @abstractmethod
    async def handle(self, command: Command) -> None:
        """
        contiene la lógica de negocio para procesar el comando

        este método es invocado por el `commandbus`

        args:
            command: la instancia del comando a procesar
        """
        raise NotImplementedError

    def listen_to(self) -> Type[Command]:
        """
        especifica a qué tipo de comando se suscribe este handler

        el `commandbus` utiliza este método para registrar el handler y saber
        a cuál invocar para un comando dado

        returns:
            el tipo de la clase del comando (eg `startrecordingcommand`)
        """
        raise NotImplementedError
