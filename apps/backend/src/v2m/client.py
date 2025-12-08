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
cliente de línea de comandos para comunicarse con el daemon de v2m

este módulo proporciona funcionalidades para enviar comandos al daemon
de voice2machine a través de un socket unix es la forma principal de
interactuar con el servicio desde scripts externos o la terminal

el cliente establece una conexión efímera con el socket del daemon
envía el comando y espera una respuesta antes de cerrar la conexión

ejemplo
    uso desde línea de comandos::

        python -m v2m.client START_RECORDING
        python -m v2m.client STOP_RECORDING
        python -m v2m.client PING

    uso programático::

        import asyncio
        from v2m.client import send_command

        response = asyncio.run(send_command("PING"))
        print(response)  # "PONG"

note
    el daemon debe estar ejecutándose antes de enviar comandos
    iniciar con ``python -m v2m.main --daemon``
"""

import asyncio
import sys
import argparse
from v2m.core.ipc_protocol import SOCKET_PATH, IPCCommand, MAX_MESSAGE_SIZE

async def send_command(command: str) -> str:
    """
    envía un comando al daemon a través de un socket unix

    establece una conexión asíncrona con el socket del daemon envía el
    comando codificado en utf-8 y espera una respuesta la conexión se
    cierra automáticamente después de recibir la respuesta

    args:
        command: el comando a enviar debe ser uno de los valores definidos
            en ``IPCCommand`` (ej ``START_RECORDING`` ``STOP_RECORDING``
            ``PING`` ``SHUTDOWN`` ``PROCESS_TEXT <texto>``)

    returns:
        la respuesta del daemon como cadena de texto respuestas típicas
            - ``OK`` comando ejecutado exitosamente
            - ``PONG`` respuesta al comando ping
            - ``ERROR: <mensaje>`` ocurrió un error
            - ``UNKNOWN_COMMAND`` comando no reconocido

    raises:
        SystemExit: si el daemon no está corriendo (filenotfounderror)
            o rechaza la conexión (connectionrefusederror)

    example
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
        
        # Validate outgoing message size
        if length > MAX_MESSAGE_SIZE:
            print(f"Error: Message too large ({length} bytes, max: {MAX_MESSAGE_SIZE})", file=sys.stderr)
            sys.exit(1)
        
        writer.write(length.to_bytes(4, byteorder="big"))
        writer.write(message_bytes)
        await writer.drain()

        # Read response with same framing protocol
        try:
            response_header = await reader.readexactly(4)
            response_length = int.from_bytes(response_header, byteorder="big")
            
            # Validate response length to prevent memory exhaustion
            if response_length > MAX_MESSAGE_SIZE:
                print(f"Error: Response too large ({response_length} bytes, max: {MAX_MESSAGE_SIZE})", file=sys.stderr)
                sys.exit(1)
            
            response_data = await reader.readexactly(response_length)
            response = response_data.decode("utf-8")
        except asyncio.IncompleteReadError as e:
            print(f"Error: Incomplete response from daemon (received {len(e.partial)} bytes)", file=sys.stderr)
            sys.exit(1)
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
    punto de entrada para el cliente de línea de comandos

    analiza los argumentos de la línea de comandos construye el mensaje
    ipc completo (incluyendo payload opcional) y lo envía al daemon
    imprime la respuesta recibida a stdout

    argumentos cli
        command: comando ipc a enviar (requerido) opciones
            ``START_RECORDING`` ``STOP_RECORDING`` ``PING``
            ``SHUTDOWN`` ``PROCESS_TEXT``
        payload: datos adicionales para el comando (opcional)
            solo aplicable a ``PROCESS_TEXT``

    example
        iniciar grabación::

            python -m v2m.client START_RECORDING

        procesar texto::

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
