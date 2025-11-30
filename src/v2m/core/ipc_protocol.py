"""
Protocolo de comunicación inter-procesos (IPC) para voice2machine.

Este módulo define el protocolo de comunicación entre el cliente y el daemon.
Utiliza un socket Unix para comunicación local eficiente y segura.

Protocolo:
    La comunicación es síncrona tipo request-response:

    1. El cliente abre una conexión al socket Unix.
    2. Envía un comando como texto plano (UTF-8).
    3. El daemon procesa el comando.
    4. El daemon responde con un mensaje de estado.
    5. La conexión se cierra.

Formato de comandos:
    - Comandos simples: ``COMANDO`` (ej. ``START_RECORDING``)
    - Comandos con payload: ``COMANDO <datos>`` (ej. ``PROCESS_TEXT hola mundo``)

Respuestas:
    - ``OK``: Operación exitosa.
    - ``PONG``: Respuesta a PING.
    - ``ERROR: <mensaje>``: Error durante la operación.
    - ``UNKNOWN_COMMAND``: Comando no reconocido.
    - ``SHUTTING_DOWN``: El daemon se está deteniendo.

Constantes:
    - ``SOCKET_PATH``: Ruta predeterminada del socket Unix.
"""

from enum import Enum

class IPCCommand(str, Enum):
    """Enumeración de los comandos IPC disponibles.

    Define los comandos que pueden ser enviados desde el cliente al daemon
    para controlar su comportamiento. Hereda de ``str`` para permitir
    comparación directa con cadenas de texto.

    Attributes:
        START_RECORDING: Inicia la captura de audio desde el micrófono.
            El daemon comienza a grabar y crea el archivo de bandera.
        STOP_RECORDING: Detiene la grabación actual y dispara la
            transcripción. El resultado se copia al portapapeles.
        PROCESS_TEXT: Procesa texto existente con el LLM (Gemini).
            Requiere un payload con el texto a procesar.
            Formato: ``PROCESS_TEXT <texto>``
        PING: Comando de heartbeat para verificar si el daemon está
            activo y respondiendo. Responde con ``PONG``.
        SHUTDOWN: Solicita al daemon que termine de forma ordenada.
            Limpia recursos y cierra el socket.

    Example:
        Uso en comparaciones::

            message = "START_RECORDING"
            if message == IPCCommand.START_RECORDING:
                print("Iniciando grabación...")

        Iteración sobre comandos::

            for cmd in IPCCommand:
                print(f"Comando: {cmd.value}")
    """
    START_RECORDING = "START_RECORDING"
    STOP_RECORDING = "STOP_RECORDING"
    PROCESS_TEXT = "PROCESS_TEXT"
    PING = "PING"
    SHUTDOWN = "SHUTDOWN"

SOCKET_PATH = "/tmp/v2m.sock"
