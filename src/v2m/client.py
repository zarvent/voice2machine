"""
Cliente de línea de comandos para comunicarse con el daemon de v2m.

Este módulo proporciona funcionalidades para enviar comandos al daemon
de voice2machine a través de un socket Unix. Es la forma principal de
interactuar con el servicio desde scripts externos o la terminal.

El cliente establece una conexión efímera con el socket del daemon,
envía el comando y espera una respuesta antes de cerrar la conexión.

Ejemplo:
    Uso desde línea de comandos::

        python -m v2m.client START_RECORDING
        python -m v2m.client STOP_RECORDING
        python -m v2m.client PING

    Uso programático::

        import asyncio
        from v2m.client import send_command

        response = asyncio.run(send_command("PING"))
        print(response)  # "PONG"

Note:
    El daemon debe estar ejecutándose antes de enviar comandos.
    Iniciar con: ``python -m v2m.main --daemon``
"""

import asyncio
import sys
import argparse
from v2m.core.ipc_protocol import SOCKET_PATH, IPCCommand

async def send_command(command: str) -> str:
    """Envía un comando al daemon a través de un socket Unix.

    Establece una conexión asíncrona con el socket del daemon, envía el
    comando codificado en UTF-8 y espera una respuesta. La conexión se
    cierra automáticamente después de recibir la respuesta.

    Args:
        command: El comando a enviar. Debe ser uno de los valores definidos
            en ``IPCCommand`` (ej. ``START_RECORDING``, ``STOP_RECORDING``,
            ``PING``, ``SHUTDOWN``, ``PROCESS_TEXT <texto>``).

    Returns:
        La respuesta del daemon como cadena de texto. Respuestas típicas:
            - ``OK``: Comando ejecutado exitosamente.
            - ``PONG``: Respuesta al comando PING.
            - ``ERROR: <mensaje>``: Ocurrió un error.
            - ``UNKNOWN_COMMAND``: Comando no reconocido.

    Raises:
        SystemExit: Si el daemon no está corriendo (FileNotFoundError)
            o rechaza la conexión (ConnectionRefusedError).

    Example:
        Verificar si el daemon está activo::

            response = await send_command("PING")
            if response == "PONG":
                print("Daemon activo")
    """
    try:
        reader, writer = await asyncio.open_unix_connection(SOCKET_PATH)

        writer.write(command.encode())
        await writer.drain()

        data = await reader.read(1024)
        response = data.decode()
        # print(f"Response: {response}")

        writer.close()
        await writer.wait_closed()
        return response
    except FileNotFoundError:
        print("Error: Daemon is not running. Start it with 'python -m v2m.daemon'", file=sys.stderr)
        sys.exit(1)
    except ConnectionRefusedError:
        print("Error: Connection refused. Daemon might be dead.", file=sys.stderr)
        sys.exit(1)

def main() -> None:
    """Punto de entrada para el cliente de línea de comandos.

    Analiza los argumentos de la línea de comandos, construye el mensaje
    IPC completo (incluyendo payload opcional) y lo envía al daemon.
    Imprime la respuesta recibida a stdout.

    Argumentos CLI:
        command: Comando IPC a enviar (requerido). Opciones:
            ``START_RECORDING``, ``STOP_RECORDING``, ``PING``,
            ``SHUTDOWN``, ``PROCESS_TEXT``.
        payload: Datos adicionales para el comando (opcional).
            Solo aplicable a ``PROCESS_TEXT``.

    Example:
        Iniciar grabación::

            python -m v2m.client START_RECORDING

        Procesar texto::

            python -m v2m.client PROCESS_TEXT "texto a refinar"
    """
    parser = argparse.ArgumentParser(description="Whisper Dictation Client")
    parser.add_argument("command", choices=[e.value for e in IPCCommand], help="Command to send to daemon")
    parser.add_argument("payload", nargs="*", help="Optional payload for the command")

    args = parser.parse_args()

    full_command = args.command
    if args.payload:
        full_command += " " + " ".join(args.payload)

    response = asyncio.run(send_command(full_command))
    print(response)

if __name__ == "__main__":
    main()
