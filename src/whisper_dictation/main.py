"""
Punto de entrada principal para la aplicación de dictado por voz.

Este script actúa como el controlador CLI (Command Line Interface) que interpreta
los comandos pasados desde los scripts de shell (ej. 'start', 'stop', 'process')
y los despacha al bus de comandos de la aplicación para su procesamiento.

Funcionalidades:
- Parsear argumentos de línea de comandos para determinar la acción a ejecutar.
- Inicializar el contenedor de inyección de dependencias (DI).
- Despachar comandos a través del command bus.
- Manejar errores a nivel de aplicación y enviar notificaciones al usuario.
"""
import argparse
import sys
import subprocess
from whisper_dictation.core.di.container import container
from whisper_dictation.application.commands import StartRecordingCommand, StopRecordingCommand, ProcessTextCommand
from whisper_dictation.domain.errors import ApplicationError
from whisper_dictation.core.logging import logger

def send_notification(title: str, message: str) -> None:
    """
    Envía una notificación de escritorio al usuario.

    Utiliza el comando `notify-send` del sistema para mostrar un mensaje emergente.
    Esto es útil para comunicar errores o estados importantes sin necesidad de
    una interfaz gráfica completa.

    Args:
        title (str): El título de la notificación.
        message (str): El cuerpo del mensaje de la notificación.
    """
    subprocess.run(["notify-send", title, message])

def main() -> None:
    """
    Función principal que orquesta la aplicación CLI.

    Configura el parser de argumentos, recibe los comandos y utiliza el
    command bus para ejecutar la lógica de negocio correspondiente.
    También implementa un manejo de errores global para capturar y notificar
    cualquier problema que ocurra durante la ejecución.
    """
    # --- Configuración del parser de argumentos ---
    # Se define la interfaz de línea de comandos que aceptará la aplicación.
    parser = argparse.ArgumentParser(description="Whisper Dictation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("start", help="Inicia la grabación de audio.")
    subparsers.add_parser("stop", help="Detiene la grabación y transcribe el audio.")
    subparsers.add_parser("process", help="Procesa el texto del portapapeles con un LLM.")

    args, unknown = parser.parse_known_args()

    # --- Inicialización del Command Bus ---
    # Se obtiene una instancia del command bus desde el contenedor de DI.
    # El command bus es el responsable de mapear un comando a su handler correspondiente.
    command_bus = container.get_command_bus()

    try:
        # --- Despacho de comandos ---
        # Se evalúa el comando proporcionado y se crea la instancia del
        # comando correspondiente para despacharlo al bus.
        if args.command == "start":
            command_bus.dispatch(StartRecordingCommand())
        elif args.command == "stop":
            command_bus.dispatch(StopRecordingCommand())
        elif args.command == "process":
            # Para el comando 'process', el texto a procesar puede venir
            # del stdin (pipe) o como argumentos adicionales.
            text_to_process = ""
            if not sys.stdin.isatty():
                text_to_process = sys.stdin.read().strip()
            elif unknown:
                text_to_process = " ".join(unknown)

            if text_to_process:
                command_bus.dispatch(ProcessTextCommand(text_to_process))
            else:
                # Si no se proporciona texto, es un uso incorrecto del comando.
                raise ValueError("No se proporcionó texto para procesar.")

    except ApplicationError as e:
        # --- Manejo de errores de la aplicación ---
        # Captura errores de negocio conocidos (ej. micrófono no encontrado)
        # y los notifica de forma amigable.
        logger.error(str(e))
        send_notification("❌ Error", str(e))
        sys.exit(1)
    except Exception as e:
        # --- Manejo de errores inesperados ---
        # Captura cualquier otro error no previsto para evitar que la aplicación
        # se cierre silenciosamente.
        logger.exception("Ocurrió un error inesperado.")
        send_notification("❌ Error Inesperado", "Ocurrió un error inesperado.")
        sys.exit(1)

if __name__ == "__main__":
    main()
