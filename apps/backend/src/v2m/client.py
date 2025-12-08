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
CLIENTE DE LÍNEA DE COMANDOS PARA COMUNICARSE CON EL DAEMON DE V2M

este módulo proporciona funcionalidades para enviar comandos al daemon
de voice2machine a través de un socket unix es la forma principal de
interactuar con el servicio desde scripts externos o la terminal

el cliente establece una conexión efímera con el socket del daemon
envía el comando y espera una respuesta antes de cerrar la conexión

EJEMPLO
    uso desde línea de comandos::

        python -m v2m.client START_RECORDING
        python -m v2m.client STOP_RECORDING
        python -m v2m.client PING

    uso programático::

        import asyncio
        from v2m.client import send_command

        response = asyncio.run(send_command("PING"))
        print(response)  # "pong"

NOTE
    el daemon debe estar ejecutándose antes de enviar comandos
    iniciar con ``python -m v2m.main --daemon``
"""

import asyncio
import sys
import argparse
from v2m.core.ipc_protocol import SOCKET_PATH, IPCCommand

async def send_command(command: str) -> str:
    """
    ENVÍA UN COMANDO AL DAEMON A TRAVÉS DE UN SOCKET UNIX

    establece una conexión asíncrona con el socket del daemon envía el
    comando codificado en utf-8 y espera una respuesta la conexión se
    cierra automáticamente después de recibir la respuesta

    ARGS
        command: el comando a enviar debe ser uno de los valores definidos
            en ``IPCCommand`` (ej ``START_RECORDING`` ``STOP_RECORDING``
            ``PING`` ``SHUTDOWN`` ``PROCESS_TEXT <texto>``)

    RETURNS
        la respuesta del daemon como cadena de texto respuestas típicas
            - ``OK`` comando ejecutado exitosamente
            - ``PONG`` respuesta al comando ping
            - ``ERROR: <mensaje>`` ocurrió un error
            - ``UNKNOWN_COMMAND`` comando no reconocido

    RAISES
        SystemExit: si el daemon no está corriendo (filenotfounderror)
            o rechaza la conexión (connectionrefusederror)

    EXAMPLE
        verificar si el daemon está activo::

            response = await send_command("PING")
            if response == "PONG":
                print("Daemon activo")
    """
    try:
        reader, writer = await asyncio.open_unix_connection(SOCKET_PATH)

        # Protocolo de framing: 4 bytes longitud (Big Endian) + Payload
        message_bytes = command.encode("utf-8")
        length = len(message_bytes)
        writer.write(length.to_bytes(4, byteorder="big"))
        writer.write(message_bytes)
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
    """
    PUNTO DE ENTRADA PARA EL CLIENTE DE LÍNEA DE COMANDOS

    analiza los argumentos de la línea de comandos construye el mensaje
    ipc completo (incluyendo payload opcional) y lo envía al daemon
    imprime la respuesta recibida a stdout

    ARGUMENTOS CLI
        command: comando ipc a enviar (requerido) opciones
            ``START_RECORDING`` ``STOP_RECORDING`` ``PING``
            ``SHUTDOWN`` ``PROCESS_TEXT``
        payload: datos adicionales para el comando (opcional)
            solo aplicable a ``PROCESS_TEXT``

    EXAMPLE
        iniciar grabación::

            python -m v2m.client START_RECORDING

        procesar texto::

            python -m v2m.client PROCESS_TEXT "texto a refinar"
    """
    parser = argparse.ArgumentParser(description="cliente de dictado whisper")
    parser.add_argument("command", choices=[e.value for e in IPCCommand], help="comando para enviar al daemon")
    parser.add_argument("payload", nargs="*", help="payload opcional para el comando")

    args = parser.parse_args()

    full_command = args.command
    if args.payload:
        full_command += " " + " ".join(args.payload)

    response = asyncio.run(send_command(full_command))
    print(response)

if __name__ == "__main__":
    main()
