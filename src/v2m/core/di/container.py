"""
módulo que implementa el contenedor de inyección de dependencias (DI)

el contenedor es responsable de "cablear" la aplicación esto significa que
instancia las clases concretas (infraestructura) y las inyecta en las clases
que las necesitan (handlers de aplicación) desacoplando las capas entre sí

este es el único lugar de la aplicación donde las implementaciones concretas
(ej `whispertranscriptionservice`) son conocidas el resto de la aplicación
depende de abstracciones (interfaces)
"""

from v2m.core.cqrs.command_bus import CommandBus
from v2m.application.command_handlers import StartRecordingHandler, StopRecordingHandler, ProcessTextHandler
from v2m.infrastructure.whisper_transcription_service import WhisperTranscriptionService
from v2m.infrastructure.gemini_llm_service import GeminiLLMService
from v2m.infrastructure.linux_adapters import LinuxNotificationAdapter, LinuxClipboardAdapter
from v2m.application.transcription_service import TranscriptionService
from v2m.application.llm_service import LLMService
from v2m.core.interfaces import NotificationInterface, ClipboardInterface

from v2m.infrastructure.vad_service import VADService
from v2m.core.logging import logger
import threading

class Container:
    """
    contenedor de DI que gestiona el ciclo de vida y las dependencias de los objetos
    """
    def __init__(self) -> None:
        """
        inicializa y configura todas las dependencias de la aplicación

        el proceso de configuración sigue estos pasos
        1.  **instanciar servicios de infraestructura** se crean las implementaciones
            concretas de los servicios (ej para WHISPER para GEMINI) se manejan
            como singletons para que solo haya una instancia por servicio

        2.  **instanciar handlers de aplicación** se crean los manejadores de comandos
            y se les inyectan las instancias de los servicios que necesitan para
            funcionar

        3.  **configurar el command bus** se instancia el bus de comandos y se
            registran todos los handlers para que el bus sepa a quién despachar
            cada comando
        """
        # --- 1 instanciar servicios (como singletons) ---
        # aquí se decide qué implementación concreta usar para cada interfaz
        # si quisiéramos cambiar de GEMINI a OPENAI solo cambiaríamos esta línea
        self.vad_service = VADService()
        self.transcription_service: TranscriptionService = WhisperTranscriptionService(vad_service=self.vad_service)
        # precargar el modelo whisper en un hilo para evitar bloqueo al primer uso
        def _preload_whisper():
            try:
                _ = self.transcription_service.model
                logger.info("Whisper precargado correctamente")
            except Exception as e:
                logger.warning(f"No se pudo precargar Whisper: {e}")
        threading.Thread(target=_preload_whisper, daemon=True).start()
        self.llm_service: LLMService = GeminiLLMService()

        # adaptadores de sistema
        self.notification_service: NotificationInterface = LinuxNotificationAdapter()
        self.clipboard_service: ClipboardInterface = LinuxClipboardAdapter()

        # --- 2 instanciar manejadores de comandos ---
        # se inyectan las dependencias en el constructor de cada handler
        self.start_recording_handler = StartRecordingHandler(
            self.transcription_service,
            self.notification_service
        )
        self.stop_recording_handler = StopRecordingHandler(
            self.transcription_service,
            self.notification_service,
            self.clipboard_service
        )
        self.process_text_handler = ProcessTextHandler(
            self.llm_service,
            self.notification_service,
            self.clipboard_service
        )

        # --- 3 instanciar y configurar el bus de comandos ---
        # el bus de comandos se convierte en el punto de acceso central para
        # ejecutar la lógica de negocio
        self.command_bus = CommandBus()
        self.command_bus.register(self.start_recording_handler)
        self.command_bus.register(self.stop_recording_handler)
        self.command_bus.register(self.process_text_handler)

    def get_command_bus(self) -> CommandBus:
        """
        provee acceso al command bus configurado

        returns:
            la instancia única del command bus
        """
        return self.command_bus

# --- instancia global del contenedor ---
# se crea una única instancia del contenedor que será accesible desde toda la
# aplicación (principalmente desde `main.py`)
container = Container()
