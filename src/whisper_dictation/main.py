"""
punto de entrada principal para la aplicación de dictado por voz

este script ahora actúa como un lanzador unificado puede iniciar el demonio (servidor)
o actuar como un cliente que envía comandos al demonio a través de IPC

modos de operación
1.  daemon `python -m whisper_dictation.main --daemon`
    inicia el proceso persistente que carga el modelo en memoria y escucha comandos

2.  client `python -m whisper_dictation.main <COMMAND>`
    envía un comando (START_RECORDING STOP_RECORDING etc) al demonio en ejecución
"""
import argparse
import asyncio
import sys
from whisper_dictation.daemon import Daemon
from whisper_dictation.client import send_command
from whisper_dictation.core.ipc_protocol import IPCCommand
from whisper_dictation.core.logging import logger

def main() -> None:
    parser = argparse.ArgumentParser(description="Whisper Dictation Main Entrypoint")

    # argumento para iniciar como demonio
    parser.add_argument("--daemon", action="store_true", help="Start the background daemon process")

    # argumento para enviar comandos (modo cliente)
    parser.add_argument("command", nargs="?", choices=[e.value for e in IPCCommand], help="IPC Command to send")
    parser.add_argument("payload", nargs="*", help="Optional payload for the command")

    args = parser.parse_args()

    if args.daemon:
        logger.info("Starting Whisper Dictation Daemon...")
        daemon = Daemon()
        daemon.run()
    elif args.command:
        # modo cliente
        try:
            full_command = args.command
            if args.payload:
                full_command += " " + " ".join(args.payload)

            response = asyncio.run(send_command(full_command))
            print(response)
        except Exception as e:
            print(f"Error sending command: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
