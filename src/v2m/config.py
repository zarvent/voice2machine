"""
Módulo de configuración de la aplicación voice2machine.

Este módulo proporciona un sistema de configuración robusto y tipado utilizando
Pydantic Settings. Soporta múltiples fuentes de configuración con la siguiente
prioridad (de mayor a menor):

    1. Argumentos de inicialización (constructor).
    2. Variables de entorno.
    3. Archivo .env.
    4. Archivo config.toml.
    5. Valores por defecto.

La configuración está organizada en secciones lógicas:
    - ``PathsConfig``: Rutas de archivos temporales y del sistema.
    - ``WhisperConfig``: Parámetros del modelo de transcripción.
    - ``GeminiConfig``: Configuración del servicio LLM.

Ejemplo:
    Acceder a la configuración desde cualquier parte de la aplicación::

        from v2m.config import config

        # Acceder a configuración de Whisper
        modelo = config.whisper.model
        dispositivo = config.whisper.device

        # Acceder a rutas
        archivo_audio = config.paths.audio_file

Notas:
    - El archivo config.toml debe estar en la raíz del proyecto.
    - Las variables de entorno tienen prefijo automático del nombre de la sección.
    - GEMINI_API_KEY debe definirse en el archivo .env o como variable de entorno.
"""

from pathlib import Path
from typing import Optional, Tuple, Type
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
    TomlConfigSettingsSource,
)

# --- ruta base del proyecto ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class PathsConfig(BaseModel):
    """Configuración de rutas de archivos y directorios para la aplicación.

    Esta clase define las rutas utilizadas por el sistema para almacenar
    archivos temporales, banderas de estado y registros de depuración.

    Attributes:
        recording_flag: Ruta al archivo PID que indica una grabación activa.
            Se crea cuando inicia la grabación y se elimina al terminar.
        audio_file: Ruta al archivo WAV temporal donde se guarda el audio
            grabado antes de la transcripción.
        log_file: Ruta al archivo de registro para depuración y diagnóstico.
        venv_path: Ruta al entorno virtual de Python de la aplicación.
            Utilizado por los scripts de shell para activar el entorno.

    Example:
        Acceder a las rutas configuradas::

            from v2m.config import config

            if config.paths.recording_flag.exists():
                print("Hay una grabación en progreso")
    """
    recording_flag: Path = Field(default=Path("/tmp/v2m_recording.pid"))
    audio_file: Path = Field(default=Path("/tmp/v2m_audio.wav"))
    log_file: Path = Field(default=Path("/tmp/v2m_debug.log"))
    venv_path: Path = Field(default=Path("~/v2m/venv"))

    def __getitem__(self, item):
        return getattr(self, item)

class VadParametersConfig(BaseModel):
    """Parámetros para la detección de actividad de voz (VAD).

    El VAD (Voice Activity Detection) filtra los segmentos de silencio del audio
    antes de enviarlos al modelo de transcripción, mejorando la eficiencia y
    reduciendo alucinaciones en pausas largas.

    Attributes:
        threshold: Umbral de probabilidad (0.0 a 1.0) para clasificar un
            segmento como voz. Valores más altos = detección más estricta.
            Por defecto 0.5.
        min_speech_duration_ms: Duración mínima en milisegundos que debe tener
            un segmento de audio para ser considerado como habla. Filtra
            ruidos breves. Por defecto 250ms.
        min_silence_duration_ms: Duración mínima del silencio en milisegundos
            requerida para considerar que el habla terminó. Valores más altos
            permiten pausas más largas dentro de una oración. Por defecto 500ms.

    Note:
        Estos parámetros se pasan directamente a faster-whisper cuando
        ``vad_filter=True`` está habilitado en WhisperConfig.
    """
    threshold: float = 0.3
    min_speech_duration_ms: int = 250
    min_silence_duration_ms: int = 500
    backend: str = "torch"  # 'onnx' o 'torch'. Torch es más pesado pero más robusto históricamente.

    def __getitem__(self, item):
        return getattr(self, item)

class WhisperConfig(BaseModel):
    """Configuración para el modelo de transcripción Whisper.

    Define todos los parámetros necesarios para cargar y ejecutar el modelo
    faster-whisper, incluyendo configuración de hardware, idioma y opciones
    de decodificación.

    Attributes:
        model: Nombre o ruta del modelo Whisper a utilizar. Modelos disponibles:
            ``tiny``, ``base``, ``small``, ``medium``, ``large-v2``,
            ``large-v3``, ``large-v3-turbo``. Por defecto ``large-v2``.
        language: Código ISO 639-1 del idioma para la transcripción (ej. ``es``,
            ``en``). Usar ``auto`` para detección automática. Por defecto ``es``.
        device: Dispositivo de cómputo: ``cuda`` para GPU NVIDIA o ``cpu``.
            Por defecto ``cuda``.
        compute_type: Precisión numérica para inferencia. Opciones: ``float32``,
            ``float16``, ``int8``. GPU soporta ``float16``, CPU prefiere ``int8``.
            Por defecto ``float16``.
        device_index: Índice de la GPU a utilizar cuando hay múltiples.
            Por defecto 0 (primera GPU).
        num_workers: Número de workers para procesamiento paralelo de audio.
            Por defecto 4.
        beam_size: Tamaño del beam search durante la decodificación. Valores
            más altos mejoran calidad pero aumentan latencia. Por defecto 2.
        best_of: Número de candidatos a considerar en cada paso de
            decodificación. Por defecto 2.
        temperature: Temperatura para el muestreo. 0.0 para decodificación
            determinística (greedy). Por defecto 0.0.
        vad_filter: Si se debe aplicar filtro VAD integrado de faster-whisper
            para remover silencios. Por defecto ``True``.
        vad_parameters: Configuración detallada de los parámetros VAD.

    Example:
        Configuración típica para GPU con alta calidad::

            [whisper]
            model = "large-v3-turbo"
            device = "cuda"
            compute_type = "float16"
            beam_size = 5
    """
    model: str = "large-v2"
    language: str = "es"
    device: str = "cuda"
    compute_type: str = "float16"
    device_index: int = 0
    num_workers: int = 4
    beam_size: int = 2
    best_of: int = 2
    temperature: float = 0.0
    vad_filter: bool = True
    audio_device_index: Optional[int] = None
    vad_parameters: VadParametersConfig = Field(default_factory=VadParametersConfig)

    def __getitem__(self, item):
        return getattr(self, item)

class GeminiConfig(BaseModel):
    """Configuración para el servicio LLM de Google Gemini.

    Define los parámetros para conectarse a la API de Google Gemini y configurar
    el comportamiento del modelo de lenguaje utilizado para refinar las
    transcripciones.

    Attributes:
        model: Identificador del modelo Gemini. Formato:
            ``models/<nombre-modelo>``. Por defecto ``models/gemini-1.5-flash-latest``.
        temperature: Temperatura para la generación de texto (0.0 a 2.0).
            Valores más bajos = respuestas más determinísticas.
            Por defecto 0.3.
        max_tokens: Número máximo de tokens a generar en la respuesta.
            Por defecto 2048.
        max_input_chars: Límite de caracteres de entrada para evitar exceder
            el contexto del modelo. Por defecto 6000.
        request_timeout: Tiempo máximo de espera para una solicitud HTTP
            en segundos. Por defecto 30.
        retry_attempts: Número de reintentos automáticos ante errores
            transitorios (red, rate limiting). Por defecto 3.
        retry_min_wait: Tiempo mínimo de espera entre reintentos en segundos.
            Usado con backoff exponencial. Por defecto 2.
        retry_max_wait: Tiempo máximo de espera entre reintentos en segundos.
            Por defecto 10.
        api_key: Clave de API para autenticación con Google Cloud.
            Se recomienda definir en archivo ``.env`` como ``GEMINI_API_KEY``.

    Warning:
        La ``api_key`` es sensible y no debe incluirse en control de versiones.
        Utiliza variables de entorno o un archivo ``.env`` local.

    Example:
        Configuración en config.toml::

            [gemini]
            model = "models/gemini-1.5-pro"
            temperature = 0.2
            api_key = "${GEMINI_API_KEY}"
    """
    model: str = "models/gemini-1.5-flash-latest"
    temperature: float = 0.3
    max_tokens: int = 2048
    max_input_chars: int = 6000
    request_timeout: int = 30
    retry_attempts: int = 3
    retry_min_wait: int = 2
    retry_max_wait: int = 10
    api_key: Optional[str] = Field(default=None)

    def __getitem__(self, item):
        return getattr(self, item)

class Settings(BaseSettings):
    """Clase principal de configuración que agrupa todas las secciones.

    Esta clase actúa como el punto de acceso centralizado para toda la
    configuración de la aplicación. Utiliza Pydantic Settings para cargar
    y validar la configuración desde múltiples fuentes.

    Attributes:
        paths: Configuración de rutas de archivos y directorios.
        whisper: Configuración del modelo de transcripción Whisper.
        gemini: Configuración del servicio LLM Gemini.

    Example:
        Uso típico desde cualquier módulo::

            from v2m.config import config

            # La instancia 'config' está pre-inicializada
            print(f"Modelo Whisper: {config.whisper.model}")
            print(f"Dispositivo: {config.whisper.device}")

    Note:
        Esta clase no debe instanciarse directamente. Usar la instancia
        global ``config`` exportada por este módulo.
    """
    paths: PathsConfig = Field(default_factory=PathsConfig)
    whisper: WhisperConfig = Field(default_factory=WhisperConfig)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        toml_file=BASE_DIR / "config.toml"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """Personaliza el orden de las fuentes de configuración.

        Este método sobrescribe el comportamiento por defecto de Pydantic Settings
        para incluir archivos TOML como fuente de configuración adicional.

        El orden de prioridad resultante es (de mayor a menor):
            1. Argumentos del constructor (init_settings).
            2. Variables de entorno (env_settings).
            3. Archivo .env (dotenv_settings).
            4. Archivo config.toml (TomlConfigSettingsSource).
            5. Archivos de secretos (file_secret_settings).

        Args:
            settings_cls: La clase de configuración siendo inicializada.
            init_settings: Fuente para valores pasados al constructor.
            env_settings: Fuente para variables de entorno del sistema.
            dotenv_settings: Fuente para valores del archivo .env.
            file_secret_settings: Fuente para archivos de secretos (Docker secrets).

        Returns:
            Tupla ordenada de fuentes de configuración. Las fuentes al inicio
            tienen mayor prioridad y sobrescriben valores de fuentes posteriores.
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )

    def __getitem__(self, item):
        return getattr(self, item)

config = Settings()
