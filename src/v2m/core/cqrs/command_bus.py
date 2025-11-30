"""
Implementación del bus de comandos para el patrón CQRS.

El ``CommandBus`` es el orquestador central del sistema de comandos. Su
responsabilidad es recibir objetos ``Command`` y despacharlos al
``CommandHandler`` apropiado que ha sido registrado previamente.

Beneficios del patrón:
    - **Desacoplamiento**: El emisor del comando no conoce al receptor.
    - **Extensibilidad**: Nuevos comandos se agregan sin modificar código existente.
    - **Testabilidad**: Los handlers pueden probarse de forma aislada.
    - **Trazabilidad**: Fácil agregar logging/métricas en un punto central.

Arquitectura:
    ::

        Cliente -> CommandBus -> Handler -> Servicios
                      |
                      +-- Registro de handlers (Dict[Type[Command], Handler])

Example:
    Configuración y uso básico::

        from v2m.core.cqrs.command_bus import CommandBus

        bus = CommandBus()
        bus.register(mi_handler)

        await bus.dispatch(MiComando(datos="valor"))
"""

from typing import Dict, Type, Any
from .command import Command
from .command_handler import CommandHandler

class CommandBus:
    """Despacha comandos a sus respectivos handlers registrados.

    Actúa como un mediador (patrón Mediator) que mantiene un mapeo entre
    tipos de comando y las instancias de handlers que pueden procesarlos.

    Attributes:
        handlers: Diccionario que mapea tipos de ``Command`` a instancias
            de ``CommandHandler``. Cada tipo de comando tiene exactamente
            un handler asociado.

    Example:
        Flujo completo de configuración::

            bus = CommandBus()

            # Registrar handlers (normalmente hecho en el contenedor DI)
            bus.register(StartRecordingHandler(transcription_service))
            bus.register(StopRecordingHandler(transcription_service))

            # Despachar comandos (en tiempo de ejecución)
            await bus.dispatch(StartRecordingCommand())
    """

    def __init__(self) -> None:
        """Inicializa el bus de comandos con un registro vacío de handlers.

        El diccionario de handlers se pobla mediante llamadas sucesivas
        al método ``register()`` durante la fase de inicialización de
        la aplicación (normalmente en el contenedor de DI).
        """
        self.handlers: Dict[Type[Command], CommandHandler] = {}

    def register(self, handler: CommandHandler) -> None:
        """Registra un handler de comandos en el bus.

        Asocia el tipo de comando (obtenido de ``handler.listen_to()``) con
        la instancia del handler. Este método se llama durante la fase de
        configuración de la aplicación.

        Args:
            handler: Instancia del handler a registrar. Debe implementar
                ``CommandHandler`` y retornar el tipo de comando que
                maneja en su método ``listen_to()``.

        Raises:
            ValueError: Si ya existe un handler registrado para el mismo
                tipo de comando. Cada comando debe tener exactamente un
                handler.

        Example:
            Registro típico en el contenedor::

                bus = CommandBus()
                bus.register(StartRecordingHandler(deps))
                bus.register(StopRecordingHandler(deps))
        """
        command_type = handler.listen_to()
        if command_type in self.handlers:
            raise ValueError(f"Ya existe un handler registrado para el comando {command_type}")
        self.handlers[command_type] = handler

    async def dispatch(self, command: Command) -> Any:
        """Despacha un comando a su handler correspondiente.

        Este es el método principal utilizado en tiempo de ejecución. Busca
        el handler apropiado basado en el tipo del comando y delega la
        ejecución al método ``handle()`` del handler.

        Args:
            command: Instancia del comando a despachar. El tipo del comando
                determina qué handler será invocado.

        Returns:
            El resultado de la ejecución del método ``handle()`` del handler.
            El tipo de retorno depende de la implementación del handler
            específico (generalmente ``None`` para comandos).

        Raises:
            ValueError: Si no hay ningún handler registrado para el tipo
                de comando proporcionado.

        Example:
            Despachar comandos en el daemon::

                if message == IPCCommand.START_RECORDING:
                    await bus.dispatch(StartRecordingCommand())
                elif message == IPCCommand.STOP_RECORDING:
                    await bus.dispatch(StopRecordingCommand())
        """
        command_type = type(command)
        if command_type not in self.handlers:
            raise ValueError(f"No hay un handler registrado para el comando {command_type}")
        return await self.handlers[command_type].handle(command)
