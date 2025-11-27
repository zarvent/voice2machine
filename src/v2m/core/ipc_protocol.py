"""
modulo que define el protocolo de comunicacion inter-procesos (ipc).

contiene las definiciones de los comandos y constantes utilizadas para
la comunicacion entre el cliente y el demonio.
"""
from enum import Enum

class IPCCommand(str, Enum):
    """
    enumeracion de los comandos ipc disponibles.

    define los comandos que pueden ser enviados desde el cliente al demonio
    para controlar su comportamiento.

    atributos:
        START_RECORDING: inicia la grabacion de audio.
        STOP_RECORDING: detiene la grabacion y comienza la transcripcion.
        PROCESS_TEXT: procesa texto existente (refinado con llm).
        PING: verifica si el demonio esta respondiendo.
        SHUTDOWN: detiene el demonio.
    """
    START_RECORDING = "START_RECORDING"
    STOP_RECORDING = "STOP_RECORDING"
    PROCESS_TEXT = "PROCESS_TEXT"
    PING = "PING"
    SHUTDOWN = "SHUTDOWN"

SOCKET_PATH = "/tmp/v2m.sock"
