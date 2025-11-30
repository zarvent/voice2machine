"""
Interfaz base para los manejadores de comandos (Command Handlers).

Este módulo define la clase abstracta ``CommandHandler`` que establece el
contrato que deben cumplir todos los handlers de comandos en la aplicación.

En el patrón CQRS, un handler es el componente que contiene la lógica de
negocio para procesar un tipo específico de comando. Cada handler:

    - Se suscribe a exactamente un tipo de comando.
    - Es invocado por el ``CommandBus`` cuando llega un comando de su tipo.
    - Coordina los servicios de dominio e infraestructura necesarios.

Responsabilidades de un handler:
    - Validar los datos del comando (si es necesario).
    - Orquestar llamadas a servicios de dominio e infraestructura.
    - Manejar errores y traducirlos a respuestas apropiadas.
    - NO contener lógica de dominio compleja (delegarla a servicios).

Example:
    Implementación de un handler::

        class EnviarEmailHandler(CommandHandler):
            def __init__(self, email_service: EmailService):
                self.email_service = email_service

            async def handle(self, command: EnviarEmailCommand) -> None:
                await self.email_service.enviar(
                    command.destinatario,
                    command.asunto
                )

            def listen_to(self) -> Type[Command]:
                return EnviarEmailCommand
"""

from abc import ABC, abstractmethod
from typing import Type
from .command import Command

class CommandHandler(ABC):
    """Clase base abstracta para los manejadores de comandos.

    Todos los handlers de la aplicación deben heredar de esta clase e
    implementar los métodos abstractos ``handle()`` y ``listen_to()``.

    El ciclo de vida de un handler es:
        1. Se instancia durante la configuración (con dependencias inyectadas).
        2. Se registra en el ``CommandBus``.
        3. Es invocado cada vez que llega un comando de su tipo.

    Note:
        Los handlers deben ser stateless o manejar su estado de forma
        thread-safe, ya que pueden ser invocados concurrentemente.
    """

    @abstractmethod
    async def handle(self, command: Command) -> None:
        """Procesa el comando ejecutando la lógica de negocio correspondiente.

        Este método es invocado por el ``CommandBus`` cuando un comando del
        tipo apropiado es despachado. Debe coordinar las operaciones necesarias
        utilizando los servicios inyectados en el constructor.

        Args:
            command: La instancia del comando a procesar. El tipo concreto
                corresponde al tipo retornado por ``listen_to()``.

        Note:
            Este método es asíncrono para soportar operaciones I/O bound
            (llamadas a APIs, acceso a disco, etc.) sin bloquear.

        Raises:
            Puede lanzar excepciones de dominio (``ApplicationError`` y
            subclases) que serán capturadas por el daemon y convertidas
            en respuestas de error apropiadas.
        """
        raise NotImplementedError

    def listen_to(self) -> Type[Command]:
        """Especifica a qué tipo de comando se suscribe este handler.

        El ``CommandBus`` utiliza este método durante el registro para
        construir el mapeo tipo-de-comando -> handler. Cuando un comando
        es despachado, el bus consulta este mapeo para determinar qué
        handler debe procesarlo.

        Returns:
            El tipo (clase) del comando que este handler puede procesar.
            Por ejemplo, ``StartRecordingCommand`` (la clase, no una instancia).

        Example:
            Implementación típica::

                def listen_to(self) -> Type[Command]:
                    return MiComandoEspecifico
        """
        raise NotImplementedError
