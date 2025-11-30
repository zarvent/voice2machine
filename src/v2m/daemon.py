"""
Daemon principal de voice2machine.

Este módulo implementa el proceso daemon que mantiene el modelo Whisper
cargado en memoria y escucha comandos IPC a través de un socket Unix.
El daemon es el componente central de la arquitectura, responsable de:

    - Mantener el modelo de transcripción precargado para respuesta rápida.
    - Escuchar y procesar comandos IPC de los clientes.
    - Despachar comandos al bus de comandos (patrón CQRS).
    - Gestionar el ciclo de vida del servicio.

Arquitectura:
    El daemon utiliza asyncio para manejar múltiples conexiones de clientes
    de forma concurrente. Los comandos recibidos son despachados al
    ``CommandBus`` que los redirige al handler apropiado.

    Socket Unix -> Daemon -> CommandBus -> Handler -> Servicios

Ejemplo:
    Iniciar el daemon directamente::

        python -m v2m.daemon

    O a través del punto de entrada principal::

        python -m v2m.main --daemon

Note:
    El daemon debe ejecutarse con permisos para acceder al micrófono
    y crear archivos en /tmp/.
"""

import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Callable, Dict

from v2m.core.logging import logger
from v2m.core.ipc_protocol import SOCKET_PATH, IPCCommand
from v2m.core.di.container import container
from v2m.application.commands import StartRecordingCommand, StopRecordingCommand, ProcessTextCommand
from v2m.config import config

class Daemon:
    """Clase principal del daemon que gestiona el ciclo de vida y las comunicaciones IPC.

    El daemon es un proceso persistente diseñado para ejecutarse en segundo plano.
    Mantiene el modelo Whisper en memoria para evitar tiempos de carga en cada
    transcripción y proporciona una interfaz IPC para recibir comandos.

    Attributes:
        running: Indica si el daemon está activo y procesando comandos.
        socket_path: Ruta al archivo del socket Unix para comunicación IPC.
        command_bus: Instancia del bus de comandos para despachar operaciones.

    Example:
        Iniciar el daemon::

            daemon = Daemon()
            daemon.run()  # Bloquea hasta SIGTERM o SIGINT

    Warning:
        Solo debe haber una instancia del daemon ejecutándose a la vez.
        El daemon detecta instancias previas mediante el socket Unix.
    """
    def __init__(self) -> None:
        """Inicializa la instancia del daemon.

        Configura la ruta del socket, obtiene el bus de comandos del contenedor
        de inyección de dependencias y limpia archivos huérfanos de ejecuciones
        anteriores que pudieron terminar de forma inesperada.

        Note:
            Si existe un archivo de bandera de grabación de una ejecución
            anterior (crash), será eliminado automáticamente.
        """
        self.running = False
        self.socket_path = Path(SOCKET_PATH)
        self.command_bus = container.get_command_bus()

        # limpiar flag de grabación si existe (recuperación de crash)
        if config.paths.recording_flag.exists():
            logger.warning("Limpiando flag de grabación huérfano")
            config.paths.recording_flag.unlink()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Maneja las conexiones entrantes de clientes IPC.

        Este método es llamado por el servidor asyncio para cada nueva conexión.
        Lee el mensaje del socket, lo decodifica, ejecuta el comando correspondiente
        y envía una respuesta al cliente.

        Args:
            reader: Flujo de lectura asíncrono para recibir datos del cliente.
            writer: Flujo de escritura asíncrono para enviar respuestas al cliente.

        Comandos soportados:
            - ``START_RECORDING``: Inicia la grabación de audio.
            - ``STOP_RECORDING``: Detiene y transcribe el audio.
            - ``PROCESS_TEXT <texto>``: Refina el texto con LLM.
            - ``PING``: Verifica que el daemon esté activo (responde PONG).
            - ``SHUTDOWN``: Detiene el daemon de forma ordenada.

        Note:
            Los errores durante el procesamiento de comandos son capturados
            y devueltos como respuesta ``ERROR: <mensaje>`` sin terminar
            la conexión del daemon.
        """
        data = await reader.read(4096)
        message = data.decode().strip()
        logger.info(f"Received IPC message: {message}")

        response = "OK"

        try:
            if message == IPCCommand.START_RECORDING:
                await self.command_bus.dispatch(StartRecordingCommand())

            elif message == IPCCommand.STOP_RECORDING:
                await self.command_bus.dispatch(StopRecordingCommand())

            elif message.startswith(IPCCommand.PROCESS_TEXT):
                # extraer payload
                parts = message.split(" ", 1)
                if len(parts) > 1:
                    text = parts[1]
                    await self.command_bus.dispatch(ProcessTextCommand(text))
                else:
                    response = "ERROR: Missing text payload"

            elif message == IPCCommand.PING:
                response = "PONG"

            elif message == IPCCommand.SHUTDOWN:
                self.running = False
                response = "SHUTTING_DOWN"

            else:
                logger.warning(f"Unknown command: {message}")
                response = "UNKNOWN_COMMAND"

        except Exception as e:
            logger.error(f"Error handling command {message}: {e}")
            response = f"ERROR: {str(e)}"

        writer.write(response.encode())
        await writer.drain()
        writer.close()

        if message == IPCCommand.SHUTDOWN:
            self.stop()

    async def start_server(self) -> None:
        """Inicia el servidor de socket Unix.

        Verifica si existe un socket previo y determina si hay otro daemon
        activo. Si el socket existe pero no hay daemon escuchando, lo elimina
        y crea uno nuevo.

        Raises:
            SystemExit: Si ya hay otro daemon activo escuchando en el socket.

        Note:
            Este método bloquea indefinidamente hasta que se llame a ``stop()``
            o se reciba una señal de terminación.
        """
        if self.socket_path.exists():
            # verificar si el socket está realmente vivo
            try:
                reader, writer = await asyncio.open_unix_connection(str(self.socket_path))
                writer.close()
                await writer.wait_closed()
                logger.error("Daemon is already running.")
                sys.exit(1)
            except (ConnectionRefusedError, FileNotFoundError):
                # el socket existe pero nadie está escuchando es seguro eliminarlo
                self.socket_path.unlink()

        server = await asyncio.start_unix_server(self.handle_client, str(self.socket_path))
        logger.info(f"Daemon listening on {self.socket_path}")

        self.running = True

        # mantener el servidor en funcionamiento
        async with server:
            await server.serve_forever()

    def stop(self) -> None:
        """Detiene el daemon y libera recursos.

        Realiza una limpieza ordenada eliminando el archivo del socket Unix
        y terminando el proceso. Este método es llamado automáticamente al
        recibir señales SIGINT o SIGTERM, o al procesar el comando SHUTDOWN.

        Raises:
            SystemExit: Siempre termina con código 0 (exit exitoso).
        """
        logger.info("Stopping daemon...")
        if self.socket_path.exists():
            self.socket_path.unlink()
        sys.exit(0)

    def run(self) -> None:
        """Ejecuta el bucle principal del daemon.

        Configura los manejadores de señales POSIX (SIGINT, SIGTERM) para
        permitir una terminación ordenada, crea un nuevo event loop de asyncio
        y ejecuta el servidor hasta que sea detenido.

        Este método es bloqueante y no retorna hasta que el daemon termine.

        Señales manejadas:
            - ``SIGINT``: Interrupción de teclado (Ctrl+C).
            - ``SIGTERM``: Señal de terminación estándar.

        Example:
            Uso típico::

                if __name__ == "__main__":
                    daemon = Daemon()
                    daemon.run()
        """
        # configurar manejadores de señales
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        def signal_handler():
            logger.info("Signal received, shutting down...")
            self.stop()

        # nota add_signal_handler no es compatible con windows pero estamos en linux
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTERM, signal_handler)

        try:
            loop.run_until_complete(self.start_server())
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

if __name__ == "__main__":
    daemon = Daemon()
    daemon.run()
