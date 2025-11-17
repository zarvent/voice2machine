"""
Módulo que contiene los manejadores de comandos (Command Handlers).

Los handlers son el corazón de la lógica de negocio de la aplicación.
Cada handler se suscribe a un tipo de comando específico y ejecuta las acciones
correspondientes cuando ese comando es despachado por el Command Bus.

Este enfoque, inspirado en CQRS (Command Query Responsibility Segregation),
permite un bajo acoplamiento entre el punto de entrada de la aplicación (main.py)
y la lógica de negocio real.
"""

import subprocess
from typing import Type
from whisper_dictation.core.cqrs.command import Command
from whisper_dictation.core.cqrs.command_handler import CommandHandler
from whisper_dictation.application.commands import StartRecordingCommand, StopRecordingCommand, ProcessTextCommand
from whisper_dictation.application.transcription_service import TranscriptionService
from whisper_dictation.application.llm_service import LLMService

def send_notification(title: str, message: str) -> None:
    """Función de utilidad para enviar notificaciones de escritorio."""
    subprocess.run(["notify-send", title, message])

def copy_to_clipboard(text: str) -> None:
    """Función de utilidad para copiar texto al portapapeles del sistema."""
    subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode('utf-8'))

class StartRecordingHandler(CommandHandler):
    """
    Manejador para el comando `StartRecordingCommand`.

    Este handler interactúa con el servicio de transcripción para iniciar
    el proceso de grabación de audio. También notifica al usuario que
    la grabación ha comenzado.
    """
    def __init__(self, transcription_service: TranscriptionService) -> None:
        """
        Inicializa el handler con sus dependencias.

        Args:
            transcription_service: El servicio responsable de la grabación y transcripción.
        """
        self.transcription_service = transcription_service

    def handle(self, command: StartRecordingCommand) -> None:
        """
        Ejecuta la lógica para iniciar la grabación.

        Args:
            command: El comando que activa este handler.
        """
        self.transcription_service.start_recording()
        send_notification("🎤 Whisper", "Grabación iniciada...")

    def listen_to(self) -> Type[Command]:
        """
        Se suscribe al tipo de comando `StartRecordingCommand`.

        Returns:
            El tipo de comando que este handler puede manejar.
        """
        return StartRecordingCommand

class StopRecordingHandler(CommandHandler):
    """
    Manejador para el comando `StopRecordingCommand`.

    Este handler detiene la grabación, obtiene la transcripción del audio,
    la copia al portapapeles y notifica al usuario del resultado.
    """
    def __init__(self, transcription_service: TranscriptionService) -> None:
        """
        Inicializa el handler con sus dependencias.

        Args:
            transcription_service: El servicio responsable de la grabación y transcripción.
        """
        self.transcription_service = transcription_service

    def handle(self, command: StopRecordingCommand) -> None:
        """
        Ejecuta la lógica para detener la grabación y transcribir.

        Notifica al usuario durante el procesamiento y maneja el caso donde
        no se detecta voz en el audio.

        Args:
            command: El comando que activa este handler.
        """
        send_notification("⚡ Whisper GPU", "Procesando...")
        transcription = self.transcription_service.stop_and_transcribe()

        # Si la transcripción está vacía, no tiene sentido copiarla.
        if not transcription.strip():
            send_notification("❌ Whisper", "No se detectó voz en el audio")
            return

        copy_to_clipboard(transcription)
        preview = transcription[:80] # Se muestra una vista previa para no saturar la notificación.
        send_notification(f"✅ Whisper - Copiado", f"{preview}...")

    def listen_to(self) -> Type[Command]:
        """
        Se suscribe al tipo de comando `StopRecordingCommand`.

        Returns:
            El tipo de comando que este handler puede manejar.
        """
        return StopRecordingCommand

class ProcessTextHandler(CommandHandler):
    """
    Manejador para el comando `ProcessTextCommand`.

    Este handler utiliza un servicio de LLM (Large Language Model) para
    procesar y refinar un texto dado. El resultado se copia al portapapeles.
    """
    def __init__(self, llm_service: LLMService) -> None:
        """
        Inicializa el handler con sus dependencias.

        Args:
            llm_service: El servicio que interactúa con el LLM (ej. Gemini).
        """
        self.llm_service = llm_service

    def handle(self, command: ProcessTextCommand) -> None:
        """
        Ejecuta la lógica para procesar el texto con el LLM.

        Args:
            command: El comando que contiene el texto a procesar.
        """
        refined_text = self.llm_service.process_text(command.text)
        copy_to_clipboard(refined_text)
        send_notification("✅ Gemini - Copiado", f"{refined_text[:80]}...")

    def listen_to(self) -> Type[Command]:
        """
        Se suscribe al tipo de comando `ProcessTextCommand`.

        Returns:
            El tipo de comando que este handler puede manejar.
        """
        return ProcessTextCommand
