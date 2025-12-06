# This file is part of voice2machine.
#
# voice2machine is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""
daemon principal de voice2machine

este módulo implementa el proceso daemon que mantiene el modelo whisper
cargado en memoria y escucha comandos ipc a través de un socket unix
el daemon es el componente central de la arquitectura responsable de

    - mantener el modelo de transcripción precargado para respuesta rápida
    - escuchar y procesar comandos ipc de los clientes
    - despachar comandos al bus de comandos (patrón cqrs)
    - gestionar el ciclo de vida del servicio

arquitectura
    el daemon utiliza asyncio para manejar múltiples conexiones de clientes
    de forma concurrente los comandos recibidos son despachados al
    ``CommandBus`` que los redirige al handler apropiado

    Socket Unix -> Daemon -> CommandBus -> Handler -> Servicios

ejemplo
    iniciar el daemon directamente::

        python -m v2m.daemon

    o a través del punto de entrada principal::

        python -m v2m.main --daemon

note
    el daemon debe ejecutarse con permisos para acceder al micrófono
    y crear archivos en /tmp/
"""

import asyncio
import os
import signal
import sys
import atexit
import psutil
from pathlib import Path
from typing import Callable, Dict

from v2m.core.logging import logger
from v2m.core.ipc_protocol import SOCKET_PATH, IPCCommand
from v2m.core.di.container import container
from v2m.application.commands import StartRecordingCommand, StopRecordingCommand, ProcessTextCommand
from v2m.config import config

class Daemon:
    """
    clase principal del daemon que gestiona el ciclo de vida y las comunicaciones ipc

    el daemon es un proceso persistente diseñado para ejecutarse en segundo plano
    mantiene el modelo whisper en memoria para evitar tiempos de carga en cada
    transcripción y proporciona una interfaz ipc para recibir comandos

    attributes:
        running: indica si el daemon está activo y procesando comandos
        socket_path: ruta al archivo del socket unix para comunicación ipc
        command_bus: instancia del bus de comandos para despachar operaciones

    example
        iniciar el daemon::

            daemon = Daemon()
            daemon.run()  # Bloquea hasta SIGTERM o SIGINT

    warning
        solo debe haber una instancia del daemon ejecutándose a la vez
        el daemon detecta instancias previas mediante el socket unix
    """
    def __init__(self) -> None:
        """
        inicializa la instancia del daemon

        configura la ruta del socket obtiene el bus de comandos del contenedor
        de inyección de dependencias y limpia archivos huérfanos de ejecuciones
        anteriores que pudieron terminar de forma inesperada

        note
            si existe un archivo de bandera de grabación de una ejecución
            anterior (crash) será eliminado automáticamente
        """
        self.running = False
        self.socket_path = Path(SOCKET_PATH)
        self.pid_file = Path("/tmp/v2m_daemon.pid")
        self.command_bus = container.get_command_bus()

        # LIMPIEZA DE PROCESOS ZOMBIE (CRÍTICO)
        self._cleanup_orphaned_processes()

        # limpiar flag de grabación si existe (recuperación de crash)
        if config.paths.recording_flag.exists():
            logger.warning("Limpiando flag de grabación huérfano")
            config.paths.recording_flag.unlink()

        # Registrar cleanup automático al terminar proceso
        atexit.register(self._cleanup_resources)

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """
        maneja las conexiones entrantes de clientes ipc

        este método es llamado por el servidor asyncio para cada nueva conexión
        lee el mensaje del socket lo decodifica ejecuta el comando correspondiente
        y envía una respuesta al cliente

        args:
            reader: flujo de lectura asíncrono para recibir datos del cliente
            writer: flujo de escritura asíncrono para enviar respuestas al cliente

        comandos soportados
            - ``START_RECORDING`` inicia la grabación de audio
            - ``STOP_RECORDING`` detiene y transcribe el audio
            - ``PROCESS_TEXT <texto>`` refina el texto con llm
            - ``PING`` verifica que el daemon esté activo (responde PONG)
            - ``SHUTDOWN`` detiene el daemon de forma ordenada

        note
            los errores durante el procesamiento de comandos son capturados
            y devueltos como respuesta ``ERROR: <mensaje>`` sin terminar
            la conexión del daemon
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
        """
        inicia el servidor de socket unix

        verifica si existe un socket previo y determina si hay otro daemon
        activo si el socket existe pero no hay daemon escuchando lo elimina
        y crea uno nuevo

        raises:
            SystemExit: si ya hay otro daemon activo escuchando en el socket

        note
            este método bloquea indefinidamente hasta que se llame a ``stop()``
            o se reciba una señal de terminación
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

        # Escribir PID file para poder rastrear el proceso
        self.pid_file.write_text(str(os.getpid()))
        logger.info(f"Daemon listening on {self.socket_path} (PID: {os.getpid()})")

        self.running = True

        # mantener el servidor en funcionamiento
        async with server:
            await server.serve_forever()

    def _cleanup_orphaned_processes(self) -> None:
        """
        limpieza agresiva de todos los procesos v2m huérfanos

        esta función es crítica para ux un proceso consumiendo gpu sin
        feedback claro se interpreta como malware o minería de criptomonedas

        política zero tolerance para procesos zombie
        - mata todos los procesos v2m excepto el actual
        - libera vram inmediatamente
        - limpia todos los archivos residuales
        """
        current_pid = os.getpid()
        killed_count = 0

        try:
            # FASE 1: Matar TODOS los procesos v2m (excepto el actual)
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    # Buscar procesos v2m pero excluir el actual y herramientas del IDE
                    if ('v2m' in cmdline and
                        proc.pid != current_pid and
                        'language_server' not in cmdline and
                        'jedi' not in cmdline and
                        'health_check' not in cmdline):

                        logger.warning(f"🧹 Eliminando proceso v2m huérfano PID {proc.pid}")
                        proc.kill()
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            pass
                        killed_count += 1
                        logger.info(f"✅ Proceso {proc.pid} eliminado")

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            if killed_count > 0:
                logger.info(f"🧹 Total: {killed_count} proceso(s) zombie eliminado(s)")

                # FASE 2: Liberar VRAM inmediatamente después de matar procesos
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        # Forzar sincronización para liberar VRAM ahora
                        torch.cuda.synchronize()
                except Exception:
                    pass

            # FASE 3: Limpiar TODOS los archivos residuales
            residual_files = [
                self.pid_file,
                self.socket_path,
                Path("/tmp/v2m_recording.pid"),
            ]
            for f in residual_files:
                if f.exists():
                    try:
                        f.unlink()
                        logger.debug(f"🧹 Archivo residual eliminado: {f}")
                    except Exception:
                        pass

        except Exception as e:
            logger.warning(f"Error durante limpieza agresiva: {e}")

    def _cleanup_resources(self) -> None:
        """
        limpia recursos al terminar (llamado por atexit)

        libera vram elimina socket y pid file para prevenir procesos zombie
        """
        try:
            logger.info("🧹 Limpiando recursos del daemon...")

            # Liberar VRAM de GPU si hay modelos cargados
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logger.info("✅ VRAM liberada")
            except Exception as e:
                logger.debug(f"No se pudo liberar VRAM: {e}")

            # Eliminar socket
            if self.socket_path.exists():
                self.socket_path.unlink()
                logger.info("✅ Socket eliminado")

            # Eliminar PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
                logger.info("✅ PID file eliminado")
        except Exception as e:
            logger.error(f"Error durante cleanup: {e}")

    def stop(self) -> None:
        """
        detiene el daemon y libera recursos

        realiza una limpieza ordenada eliminando el archivo del socket unix
        y terminando el proceso este método es llamado automáticamente al
        recibir señales sigint o sigterm o al procesar el comando shutdown

        raises:
            SystemExit: siempre termina con código 0 (exit exitoso)
        """
        logger.info("Stopping daemon...")
        self._cleanup_resources()
        sys.exit(0)

    def run(self) -> None:
        """
        ejecuta el bucle principal del daemon

        configura los manejadores de señales posix (sigint sigterm) para
        permitir una terminación ordenada crea un nuevo event loop de asyncio
        y ejecuta el servidor hasta que sea detenido

        este método es bloqueante y no retorna hasta que el daemon termine

        señales manejadas
            - ``SIGINT`` interrupción de teclado (ctrl+c)
            - ``SIGTERM`` señal de terminación estándar

        example
            uso típico::

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
