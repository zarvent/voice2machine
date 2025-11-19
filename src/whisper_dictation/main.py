"""
Punto de entrada principal para la aplicación de dictado por voz.

Este script ahora actúa como un lanzador unificado. Puede iniciar el Demonio (servidor)
o actuar como un Cliente que envía comandos al Demonio a través de IPC.

Modos de operación:
1.  Daemon: `python -m whisper_dictation.main --daemon`
    Inicia el proceso persistente que carga el modelo en memoria y escucha comandos.

2.  Client: `python -m whisper_dictation.main <COMMAND>`
    Envía un comando (START_RECORDING, STOP_RECORDING, etc.) al demonio en ejecución.
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

    # Argumento para iniciar como demonio
    parser.add_argument("--daemon", action="store_true", help="Start the background daemon process")

    # Argumento para enviar comandos (modo cliente)
    parser.add_argument("command", nargs="?", choices=[e.value for e in IPCCommand], help="IPC Command to send")
    parser.add_argument("payload", nargs="*", help="Optional payload for the command")

    args = parser.parse_args()

    if args.daemon:
        logger.info("Starting Whisper Dictation Daemon...")
        daemon = Daemon()
        daemon.run()
    elif args.command:
        # Modo Cliente
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
