from whisper_dictation.core.cqrs.command_bus import CommandBus
from whisper_dictation.application.command_handlers import StartRecordingHandler, StopRecordingHandler, ProcessTextHandler
from whisper_dictation.infrastructure.whisper_transcription_service import WhisperTranscriptionService
from whisper_dictation.infrastructure.gemini_llm_service import GeminiLLMService
from whisper_dictation.application.transcription_service import TranscriptionService
from whisper_dictation.application.llm_service import LLMService

class Container:
    def __init__(self) -> None:
        # 1. Instanciar servicios (como singletons)
        self.transcription_service: TranscriptionService = WhisperTranscriptionService()
        self.llm_service: LLMService = GeminiLLMService()

        # 2. Instanciar manejadores de comandos
        self.start_recording_handler = StartRecordingHandler(self.transcription_service)
        self.stop_recording_handler = StopRecordingHandler(self.transcription_service)
        self.process_text_handler = ProcessTextHandler(self.llm_service)

        # 3. Instanciar y configurar el bus de comandos
        self.command_bus = CommandBus()
        self.command_bus.register(self.start_recording_handler)
        self.command_bus.register(self.stop_recording_handler)
        self.command_bus.register(self.process_text_handler)

    def get_command_bus(self) -> CommandBus:
        return self.command_bus

# Instancia global del contenedor
container = Container()
