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
protocolo de comunicación inter-procesos (ipc) para voice2machine

este módulo define el protocolo de comunicación entre el cliente y el daemon
utiliza un socket unix para comunicación local eficiente y segura

protocolo
    la comunicación es síncrona tipo request-response con framing de longitud
    
    **framing protocol**:
    todos los mensajes (requests y responses) usan el mismo formato:
    
    1. 4 bytes: longitud del payload (Big Endian unsigned integer)
    2. N bytes: payload utf-8
    
    ejemplo::
    
        # Enviar "PING" (4 bytes)
        \\x00\\x00\\x00\\x04PING
        
        # Recibir "PONG" (4 bytes)
        \\x00\\x00\\x00\\x04PONG

    **flujo de comunicación**:
    
    1 el cliente abre una conexión al socket unix
    2 envía longitud + comando (con payload opcional)
    3 el daemon procesa el comando
    4 el daemon responde con longitud + mensaje de estado
    5 la conexión se cierra

formato de comandos
    - comandos simples ``COMANDO`` (ej ``START_RECORDING``)
    - comandos con payload ``COMANDO <datos>`` (ej ``PROCESS_TEXT hola mundo``)

respuestas
    - ``OK`` operación exitosa
    - ``PONG`` respuesta a ping
    - ``ERROR: <mensaje>`` error durante la operación
    - ``UNKNOWN_COMMAND`` comando no reconocido
    - ``SHUTTING_DOWN`` el daemon se está deteniendo

constantes
    - ``SOCKET_PATH`` ruta predeterminada del socket unix
    - ``MAX_MESSAGE_SIZE`` tamaño máximo de mensaje (10MB) para prevenir ataques DoS
"""

from enum import Enum

class IPCCommand(str, Enum):
    """
    enumeración de los comandos ipc disponibles

    define los comandos que pueden ser enviados desde el cliente al daemon
    para controlar su comportamiento hereda de ``str`` para permitir
    comparación directa con cadenas de texto

    attributes:
        START_RECORDING: inicia la captura de audio desde el micrófono
            el daemon comienza a grabar y crea el archivo de bandera
        STOP_RECORDING: detiene la grabación actual y dispara la
            transcripción el resultado se copia al portapapeles
        PROCESS_TEXT: procesa texto existente con el llm (gemini)
            requiere un payload con el texto a procesar
            formato ``PROCESS_TEXT <texto>``
        PING: comando de heartbeat para verificar si el daemon está
            activo y respondiendo responde con ``PONG``
        SHUTDOWN: solicita al daemon que termine de forma ordenada
            limpia recursos y cierra el socket

    example
        uso en comparaciones::

            message = "START_RECORDING"
            if message == IPCCommand.START_RECORDING:
                print("Iniciando grabación...")

        iteración sobre comandos::

            for cmd in IPCCommand:
                print(f"Comando: {cmd.value}")
    """
    START_RECORDING = "START_RECORDING"
    STOP_RECORDING = "STOP_RECORDING"
    PROCESS_TEXT = "PROCESS_TEXT"
    PING = "PING"
    SHUTDOWN = "SHUTDOWN"

SOCKET_PATH = "/tmp/v2m.sock"

# Maximum message size: 10MB (prevents memory exhaustion attacks)
MAX_MESSAGE_SIZE = 10 * 1024 * 1024
