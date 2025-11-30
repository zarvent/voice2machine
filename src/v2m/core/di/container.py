"""
Contenedor de inyección de dependencias (DI) para voice2machine.

Este módulo implementa el patrón de Inyección de Dependencias que "cablea"
toda la aplicación. Es el único lugar donde las implementaciones concretas
son conocidas y donde se decide qué implementación usar para cada interfaz.

Responsabilidades del contenedor:
    1. **Instanciar servicios de infraestructura**: Crea las implementaciones
       concretas como singletons (WhisperService, GeminiService, etc.).
    2. **Instanciar handlers de aplicación**: Crea los command handlers
       inyectándoles las dependencias que necesitan.
    3. **Configurar el CommandBus**: Registra todos los handlers para que
       el bus sepa a quién despachar cada tipo de comando.

Beneficios:
    - **Desacoplamiento**: Los handlers dependen de interfaces, no implementaciones.
    - **Testabilidad**: Fácil sustituir servicios reales por mocks.
    - **Configurabilidad**: Cambiar implementaciones (ej. Gemini -> OpenAI)
      solo requiere modificar este archivo.

Diagrama de dependencias:
    ::

        Container
        ├── VADService
        ├── WhisperTranscriptionService (usa VADService)
        ├── GeminiLLMService
        ├── LinuxNotificationAdapter
        ├── LinuxClipboardAdapter
        ├── StartRecordingHandler (usa Transcription, Notification)
        ├── StopRecordingHandler (usa Transcription, Notification, Clipboard)
        ├── ProcessTextHandler (usa LLM, Notification, Clipboard)
        └── CommandBus (registra todos los handlers)

Example:
    Acceso al contenedor desde otros módulos::

        from v2m.core.di.container import container

        bus = container.get_command_bus()
        await bus.dispatch(MiComando())
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
    """Contenedor de DI que gestiona el ciclo de vida y dependencias de objetos.

    El contenedor es instanciado una única vez al inicio de la aplicación
    y proporciona acceso a los servicios configurados durante toda la
    ejecución del programa.

    Attributes:
        vad_service: Servicio de detección de actividad de voz (Silero VAD).
        transcription_service: Servicio de transcripción (faster-whisper).
        llm_service: Servicio de LLM para refinamiento de texto (Gemini).
        notification_service: Adaptador de notificaciones del sistema.
        clipboard_service: Adaptador del portapapeles del sistema.
        start_recording_handler: Handler para el comando StartRecording.
        stop_recording_handler: Handler para el comando StopRecording.
        process_text_handler: Handler para el comando ProcessText.
        command_bus: Bus de comandos configurado con todos los handlers.

    Example:
        Uso típico (ya pre-instanciado como singleton global)::

            from v2m.core.di.container import container

            # Obtener el bus de comandos
            bus = container.get_command_bus()

            # Acceso directo a servicios (menos común)
            transcription = container.transcription_service
    """
    def __init__(self) -> None:
        """Inicializa y configura todas las dependencias de la aplicación.

        El proceso de configuración sigue estos pasos:

        1. **Servicios de infraestructura** (como singletons):
           Se crean las implementaciones concretas de los servicios.
           Aquí se decide qué implementación usar para cada interfaz.
           Por ejemplo, para cambiar de Gemini a OpenAI, solo se modificaría
           esta línea.

        2. **Handlers de aplicación**:
           Se crean los manejadores de comandos inyectándoles las
           dependencias que necesitan para funcionar.

        3. **CommandBus**:
           Se configura el bus registrando todos los handlers para que
           sepa a cuál despachar cada tipo de comando.

        Note:
            El modelo Whisper se precarga en un hilo de fondo para evitar
            latencia en la primera transcripción. Si falla la precarga,
            se cargará de forma lazy en el primer uso.
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
        """Proporciona acceso al CommandBus configurado.

        Este es el punto de acceso principal para despachar comandos.
        El bus ya tiene todos los handlers registrados y está listo para usar.

        Returns:
            La instancia única del CommandBus con todos los handlers
            registrados. Usar esta instancia para despachar comandos
            desde cualquier parte de la aplicación.

        Example:
            Despachar un comando::

                bus = container.get_command_bus()
                await bus.dispatch(StartRecordingCommand())
        """
        return self.command_bus

# --- instancia global del contenedor ---
# se crea una única instancia del contenedor que será accesible desde toda la
# aplicación (principalmente desde `main.py`)
container = Container()
