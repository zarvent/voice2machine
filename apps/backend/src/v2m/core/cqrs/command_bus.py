# This file is part of voice2machine.
#
# voice2machine is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# voice2machine is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with voice2machine.  If not, see <https://www.gnu.org/licenses/>.

"""
IMPLEMENTACIÓN DEL BUS DE COMANDOS PARA EL PATRÓN CQRS

el ``CommandBus`` es el orquestador central del sistema de comandos su
responsabilidad es recibir objetos ``Command`` y despacharlos al
``CommandHandler`` apropiado que ha sido registrado previamente

BENEFICIOS DEL PATRÓN
    - **desacoplamiento** el emisor del comando no conoce al receptor
    - **extensibilidad** nuevos comandos se agregan sin modificar código existente
    - **testabilidad** los handlers pueden probarse de forma aislada
    - **trazabilidad** fácil agregar logging/métricas en un punto central

ARQUITECTURA
    ::

        Cliente -> CommandBus -> Handler -> Servicios
                      |
                      +-- Registro de handlers (Dict[Type[Command], Handler])

EXAMPLE
    configuración y uso básico::

        from v2m.core.cqrs.command_bus import CommandBus

        bus = CommandBus()
        bus.register(mi_handler)

        await bus.dispatch(MiComando(datos="valor"))
"""

from typing import Dict, Type, Any
from .command import Command
from .command_handler import CommandHandler

class CommandBus:
    """
    DESPACHA COMANDOS A SUS RESPECTIVOS HANDLERS REGISTRADOS

    actúa como un mediador (patrón mediator) que mantiene un mapeo entre
    tipos de comando y las instancias de handlers que pueden procesarlos

    ATTRIBUTES
        handlers: diccionario que mapea tipos de ``Command`` a instancias
            de ``CommandHandler`` cada tipo de comando tiene exactamente
            un handler asociado

    EXAMPLE
        flujo completo de configuración::

            bus = CommandBus()

            # registrar handlers (normalmente hecho en el contenedor di)
            bus.register(StartRecordingHandler(transcription_service))
            bus.register(StopRecordingHandler(transcription_service))

            # despachar comandos (en tiempo de ejecución)
            await bus.dispatch(StartRecordingCommand())
    """

    def __init__(self) -> None:
        """
        INICIALIZA EL BUS DE COMANDOS CON UN REGISTRO VACÍO DE HANDLERS

        el diccionario de handlers se pobla mediante llamadas sucesivas
        al método ``register()`` durante la fase de inicialización de
        la aplicación (normalmente en el contenedor de di)
        """
        self.handlers: Dict[Type[Command], CommandHandler] = {}

    def register(self, handler: CommandHandler) -> None:
        """
        REGISTRA UN HANDLER DE COMANDOS EN EL BUS

        asocia el tipo de comando (obtenido de ``handler.listen_to()``) con
        la instancia del handler este método se llama durante la fase de
        configuración de la aplicación

        ARGS
            handler: instancia del handler a registrar debe implementar
                ``CommandHandler`` y retornar el tipo de comando que
                maneja en su método ``listen_to()``

        RAISES
            ValueError: si ya existe un handler registrado para el mismo
                tipo de comando cada comando debe tener exactamente un
                handler

        EXAMPLE
            registro típico en el contenedor::

                bus = CommandBus()
                bus.register(StartRecordingHandler(deps))
                bus.register(StopRecordingHandler(deps))
        """
        command_type = handler.listen_to()
        if command_type in self.handlers:
            raise ValueError(f"Ya existe un handler registrado para el comando {command_type}")
        self.handlers[command_type] = handler

    async def dispatch(self, command: Command) -> Any:
        """
        DESPACHA UN COMANDO A SU HANDLER CORRESPONDIENTE

        este es el método principal utilizado en tiempo de ejecución busca
        el handler apropiado basado en el tipo del comando y delega la
        ejecución al método ``handle()`` del handler

        ARGS
            command: instancia del comando a despachar el tipo del comando
                determina qué handler será invocado

        RETURNS
            el resultado de la ejecución del método ``handle()`` del handler
            el tipo de retorno depende de la implementación del handler
            específico (generalmente ``None`` para comandos)

        RAISES
            ValueError: si no hay ningún handler registrado para el tipo
                de comando proporcionado

        EXAMPLE
            despachar comandos en el daemon::

                if message == IPCCommand.START_RECORDING:
                    await bus.dispatch(StartRecordingCommand())
                elif message == IPCCommand.STOP_RECORDING:
                    await bus.dispatch(StopRecordingCommand())
        """
        command_type = type(command)
        if command_type not in self.handlers:
            raise ValueError(f"No hay un handler registrado para el comando {command_type}")
        return await self.handlers[command_type].handle(command)
