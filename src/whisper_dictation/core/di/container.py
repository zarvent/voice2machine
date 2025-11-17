"""
Módulo que implementa el Contenedor de Inyección de Dependencias (DI).

El contenedor es responsable de "cablear" la aplicación. Esto significa que
instancia las clases concretas (infraestructura) y las inyecta en las clases
que las necesitan (handlers de aplicación), desacoplando las capas entre sí.

Este es el único lugar de la aplicación donde las implementaciones concretas
(ej. `WhisperTranscriptionService`) son conocidas. El resto de la aplicación
depende de abstracciones (interfaces).
"""

from whisper_dictation.core.cqrs.command_bus import CommandBus
from whisper_dictation.application.command_handlers import StartRecordingHandler, StopRecordingHandler, ProcessTextHandler
from whisper_dictation.infrastructure.whisper_transcription_service import WhisperTranscriptionService
from whisper_dictation.infrastructure.gemini_llm_service import GeminiLLMService
from whisper_dictation.application.transcription_service import TranscriptionService
from whisper_dictation.application.llm_service import LLMService

class Container:
    """
    Contenedor de DI que gestiona el ciclo de vida y las dependencias de los objetos.
    """
    def __init__(self) -> None:
        """
        Inicializa y configura todas las dependencias de la aplicación.

        El proceso de configuración sigue estos pasos:
        1.  **Instanciar servicios de infraestructura**: Se crean las implementaciones
            concretas de los servicios (ej. para Whisper, para Gemini). Se manejan
            como singletons para que solo haya una instancia por servicio.

        2.  **Instanciar handlers de aplicación**: Se crean los manejadores de comandos
            y se les inyectan las instancias de los servicios que necesitan para
            funcionar.

        3.  **Configurar el Command Bus**: Se instancia el bus de comandos y se
            registran todos los handlers para que el bus sepa a quién despachar
            cada comando.
        """
        # --- 1. Instanciar servicios (como singletons) ---
        # Aquí se decide qué implementación concreta usar para cada interfaz.
        # Si quisiéramos cambiar de Gemini a OpenAI, solo cambiaríamos esta línea.
        self.transcription_service: TranscriptionService = WhisperTranscriptionService()
        self.llm_service: LLMService = GeminiLLMService()

        # --- 2. Instanciar manejadores de comandos ---
        # Se inyectan las dependencias en el constructor de cada handler.
        self.start_recording_handler = StartRecordingHandler(self.transcription_service)
        self.stop_recording_handler = StopRecordingHandler(self.transcription_service)
        self.process_text_handler = ProcessTextHandler(self.llm_service)

        # --- 3. Instanciar y configurar el bus de comandos ---
        # El bus de comandos se convierte en el punto de acceso central para
        # ejecutar la lógica de negocio.
        self.command_bus = CommandBus()
        self.command_bus.register(self.start_recording_handler)
        self.command_bus.register(self.stop_recording_handler)
        self.command_bus.register(self.process_text_handler)

    def get_command_bus(self) -> CommandBus:
        """
        Provee acceso al Command Bus configurado.

        Returns:
            La instancia única del Command Bus.
        """
        return self.command_bus

# --- Instancia global del contenedor ---
# Se crea una única instancia del contenedor que será accesible desde toda la
# aplicación (principalmente desde `main.py`).
container = Container()
