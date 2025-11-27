"""
modulo que define la interfaz para los manejadores de comandos (command handlers).

un command handler es el componente que contiene la logica de negocio para
procesar un comando especifico. cada handler se suscribe a un tipo de comando
y es invocado por el `commandbus` cuando un comando de ese tipo es despachado.
"""

from abc import ABC, abstractmethod
from typing import Type
from .command import Command

class CommandHandler(ABC):
    """
    clase base abstracta para los manejadores de comandos.

    todos los handlers de la aplicacion deben heredar de esta clase e implementar
    los metodos `handle` y `listen_to`.
    """

    @abstractmethod
    async def handle(self, command: Command) -> None:
        """
        contiene la logica de negocio para procesar el comando.

        este metodo es invocado por el `commandbus`.

        args:
            command (Command): la instancia del comando a procesar.
        """
        raise NotImplementedError

    def listen_to(self) -> Type[Command]:
        """
        especifica a que tipo de comando se suscribe este handler.

        el `commandbus` utiliza este metodo para registrar el handler y saber
        a cual invocar para un comando dado.

        returns:
            Type[Command]: el tipo de la clase del comando (ej `startrecordingcommand`).
        """
        raise NotImplementedError
