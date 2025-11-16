import subprocess
from typing import Type
from whisper_dictation.core.cqrs.command import Command
from whisper_dictation.core.cqrs.command_handler import CommandHandler
from whisper_dictation.application.commands import StartRecordingCommand, StopRecordingCommand, ProcessTextCommand
from whisper_dictation.application.transcription_service import TranscriptionService
from whisper_dictation.application.llm_service import LLMService

def send_notification(title: str, message: str) -> None:
    subprocess.run(["notify-send", title, message])

def copy_to_clipboard(text: str) -> None:
    subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode('utf-8'))

class StartRecordingHandler(CommandHandler):
    def __init__(self, transcription_service: TranscriptionService) -> None:
        self.transcription_service = transcription_service

    def handle(self, command: StartRecordingCommand) -> None:
        self.transcription_service.start_recording()
        send_notification("🎤 Whisper", "Grabación iniciada...")

    def listen_to(self) -> Type[Command]:
        return StartRecordingCommand

class StopRecordingHandler(CommandHandler):
    def __init__(self, transcription_service: TranscriptionService) -> None:
        self.transcription_service = transcription_service

    def handle(self, command: StopRecordingCommand) -> None:
        send_notification("⚡ Whisper GPU", "Procesando...")
        transcription = self.transcription_service.stop_and_transcribe()

        if not transcription.strip():
            send_notification("❌ Whisper", "No se detectó voz en el audio")
            return

        copy_to_clipboard(transcription)
        preview = transcription[:80]
        send_notification(f"✅ Whisper - Copiado", f"{preview}...")

    def listen_to(self) -> Type[Command]:
        return StopRecordingCommand

class ProcessTextHandler(CommandHandler):
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    def handle(self, command: ProcessTextCommand) -> None:
        refined_text = self.llm_service.process_text(command.text)
        copy_to_clipboard(refined_text)
        send_notification("✅ Gemini - Copiado", f"{refined_text[:80]}...")

    def listen_to(self) -> Type[Command]:
        return ProcessTextCommand
