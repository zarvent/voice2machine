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
    """
    clase principal del demonio que maneja el ciclo de vida de la aplicacion y las comunicaciones ipc.

    esta clase es responsable de iniciar el servidor ipc, escuchar comandos entrantes
    y despacharlos al bus de comandos para su ejecucion.
    """
    def __init__(self):
        """
        inicializa la instancia del demonio.

        configura la ruta del socket, el estado de ejecucion y obtiene el bus de comandos
        del contenedor de inyeccion de dependencias.
        """
        self.running = False
        self.socket_path = Path(SOCKET_PATH)
        self.command_bus = container.get_command_bus()

        # limpiar flag de grabación si existe (recuperación de crash)
        if config.paths.recording_flag.exists():
            logger.warning("Limpiando flag de grabación huérfano")
            config.paths.recording_flag.unlink()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        maneja las conexiones entrantes de clientes ipc.

        lee el mensaje del socket, lo procesa y envia una respuesta.

        args:
            reader (asyncio.StreamReader): flujo de lectura para recibir datos.
            writer (asyncio.StreamWriter): flujo de escritura para enviar respuestas.
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

    async def start_server(self):
        """
        inicia el servidor unix socket.

        verifica si el socket ya existe y lo limpia si es necesario. luego inicia
        el servidor y espera indefinidamente hasta que se detenga.
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

    def stop(self):
        """
        detiene el demonio y limpia los recursos.

        elimina el archivo del socket y termina el proceso.
        """
        logger.info("Stopping daemon...")
        if self.socket_path.exists():
            self.socket_path.unlink()
        sys.exit(0)

    def run(self):
        """
        ejecuta el bucle principal del demonio.

        configura los manejadores de senales y ejecuta el servidor asincrono.
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
