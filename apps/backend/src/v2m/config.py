# This file is part of voice2machine.
#
# voice2machine is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# voice2machine is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with voice2machine.  If not, see <https://www.gnu.org/licenses/>.

"""
módulo de configuración de la aplicación voice2machine

este módulo proporciona un sistema de configuración robusto y tipado utilizando
pydantic settings soporta múltiples fuentes de configuración con la siguiente
prioridad (de mayor a menor)

    1 argumentos de inicialización (constructor)
    2 variables de entorno
    3 archivo .env
    4 archivo config.toml
    5 valores por defecto

la configuración está organizada en secciones lógicas
    - ``PathsConfig`` rutas de archivos temporales y del sistema
    - ``WhisperConfig`` parámetros del modelo de transcripción
    - ``GeminiConfig`` configuración del servicio llm

ejemplo
    acceder a la configuración desde cualquier parte de la aplicación::

        from v2m.config import config

        # Acceder a configuración de Whisper
        modelo = config.whisper.model
        dispositivo = config.whisper.device

        # Acceder a rutas
        archivo_audio = config.paths.audio_file

notas
    - el archivo config.toml debe estar en la raíz del proyecto
    - las variables de entorno tienen prefijo automático del nombre de la sección
    - gemini_api_key debe definirse en el archivo .env o como variable de entorno
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
    """
    configuración de rutas de archivos y directorios para la aplicación

    esta clase define las rutas utilizadas por el sistema para almacenar
    archivos temporales banderas de estado y registros de depuración

    attributes:
        recording_flag: ruta al archivo pid que indica una grabación activa
            se crea cuando inicia la grabación y se elimina al terminar
        audio_file: ruta al archivo wav temporal donde se guarda el audio
            grabado antes de la transcripción
        log_file: ruta al archivo de registro para depuración y diagnóstico
        venv_path: ruta al entorno virtual de python de la aplicación
            utilizado por los scripts de shell para activar el entorno

    example
        acceder a las rutas configuradas::

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
    """
    parámetros para la detección de actividad de voz (vad)

    el vad (voice activity detection) filtra los segmentos de silencio del audio
    antes de enviarlos al modelo de transcripción mejorando la eficiencia y
    reduciendo alucinaciones en pausas largas

    attributes:
        threshold: umbral de probabilidad (0.0 a 1.0) para clasificar un
            segmento como voz valores más altos = detección más estricta
            por defecto 0.5
        min_speech_duration_ms: duración mínima en milisegundos que debe tener
            un segmento de audio para ser considerado como habla filtra
            ruidos breves por defecto 250ms
        min_silence_duration_ms: duración mínima del silencio en milisegundos
            requerida para considerar que el habla terminó valores más altos
            permiten pausas más largas dentro de una oración por defecto 500ms

    note
        estos parámetros se pasan directamente a faster-whisper cuando
        ``vad_filter=True`` está habilitado en whisperconfig
    """
    threshold: float = 0.3
    min_speech_duration_ms: int = 250
    min_silence_duration_ms: int = 500
    backend: str = "torch"  # 'onnx' o 'torch'. Torch es más pesado pero más robusto históricamente.

    def __getitem__(self, item):
        return getattr(self, item)

class WhisperConfig(BaseModel):
    """
    configuración para el modelo de transcripción whisper

    define todos los parámetros necesarios para cargar y ejecutar el modelo
    faster-whisper incluyendo configuración de hardware idioma y opciones
    de decodificación

    attributes:
        model: nombre o ruta del modelo whisper a utilizar modelos disponibles
            ``tiny`` ``base`` ``small`` ``medium`` ``large-v2``
            ``large-v3`` ``large-v3-turbo`` por defecto ``large-v2``
        language: código iso 639-1 del idioma para la transcripción (ej ``es``
            ``en``) usar ``auto`` para detección automática por defecto ``es``
        device: dispositivo de cómputo ``cuda`` para gpu nvidia o ``cpu``
            por defecto ``cuda``
        compute_type: precisión numérica para inferencia opciones ``float32``
            ``float16`` ``int8`` gpu soporta ``float16`` cpu prefiere ``int8``
            por defecto ``float16``
        device_index: índice de la gpu a utilizar cuando hay múltiples
            por defecto 0 (primera gpu)
        num_workers: número de workers para procesamiento paralelo de audio
            por defecto 4
        beam_size: tamaño del beam search durante la decodificación valores
            más altos mejoran calidad pero aumentan latencia por defecto 2
        best_of: número de candidatos a considerar en cada paso de
            decodificación por defecto 2
        temperature: temperatura para el muestreo 0.0 para decodificación
            determinística (greedy) por defecto 0.0
        vad_filter: si se debe aplicar filtro vad integrado de faster-whisper
            para remover silencios por defecto ``True``
        vad_parameters: configuración detallada de los parámetros vad

    example
        configuración típica para gpu con alta calidad::

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
    """
    configuración para el servicio llm de google gemini

    define los parámetros para conectarse a la api de google gemini y configurar
    el comportamiento del modelo de lenguaje utilizado para refinar las
    transcripciones

    attributes:
        model: identificador del modelo gemini formato
            ``models/<nombre-modelo>`` por defecto ``models/gemini-1.5-flash-latest``
        temperature: temperatura para la generación de texto (0.0 a 2.0)
            valores más bajos = respuestas más determinísticas
            por defecto 0.3
        max_tokens: número máximo de tokens a generar en la respuesta
            por defecto 2048
        max_input_chars: límite de caracteres de entrada para evitar exceder
            el contexto del modelo por defecto 6000
        request_timeout: tiempo máximo de espera para una solicitud http
            en segundos por defecto 30
        retry_attempts: número de reintentos automáticos ante errores
            transitorios (red rate limiting) por defecto 3
        retry_min_wait: tiempo mínimo de espera entre reintentos en segundos
            usado con backoff exponencial por defecto 2
        retry_max_wait: tiempo máximo de espera entre reintentos en segundos
            por defecto 10
        api_key: clave de api para autenticación con google cloud
            se recomienda definir en archivo ``.env`` como ``GEMINI_API_KEY``

    warning
        la ``api_key`` es sensible y no debe incluirse en control de versiones
        utiliza variables de entorno o un archivo ``.env`` local

    example
        configuración en config.toml::

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


class NotificationsConfig(BaseModel):
    """
    configuración para el sistema de notificaciones del escritorio

    define parámetros para controlar el comportamiento de las notificaciones
    visuales incluyendo tiempo de expiración y cierre programático

    attributes:
        expire_time_ms: tiempo en milisegundos antes de auto-cerrar la
            notificación por defecto 3000 (3 segundos)
        auto_dismiss: si true fuerza el cierre programático via dbus
            necesario para unity/gnome que ignoran expire-time
            por defecto True

    example:
        configuración en config.toml::

            [notifications]
            expire_time_ms = 5000
            auto_dismiss = true
    """
    expire_time_ms: int = Field(default=3000, ge=500, le=30000)
    auto_dismiss: bool = Field(default=True)

    def __getitem__(self, item):
        return getattr(self, item)

class Settings(BaseSettings):
    """
    clase principal de configuración que agrupa todas las secciones

    esta clase actúa como el punto de acceso centralizado para toda la
    configuración de la aplicación utiliza pydantic settings para cargar
    y validar la configuración desde múltiples fuentes

    attributes:
        paths: configuración de rutas de archivos y directorios
        whisper: configuración del modelo de transcripción whisper
        gemini: configuración del servicio llm gemini

    example
        uso típico desde cualquier módulo::

            from v2m.config import config

            # La instancia 'config' está pre-inicializada
            print(f"Modelo Whisper: {config.whisper.model}")
            print(f"Dispositivo: {config.whisper.device}")

    note
        esta clase no debe instanciarse directamente usar la instancia
        global ``config`` exportada por este módulo
    """
    paths: PathsConfig = Field(default_factory=PathsConfig)
    whisper: WhisperConfig = Field(default_factory=WhisperConfig)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)

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
        """
        personaliza el orden de las fuentes de configuración

        este método sobrescribe el comportamiento por defecto de pydantic settings
        para incluir archivos toml como fuente de configuración adicional

        el orden de prioridad resultante es (de mayor a menor)
            1 argumentos del constructor (init_settings)
            2 variables de entorno (env_settings)
            3 archivo .env (dotenv_settings)
            4 archivo config.toml (tomlconfigsettingssource)
            5 archivos de secretos (file_secret_settings)

        args:
            settings_cls: la clase de configuración siendo inicializada
            init_settings: fuente para valores pasados al constructor
            env_settings: fuente para variables de entorno del sistema
            dotenv_settings: fuente para valores del archivo .env
            file_secret_settings: fuente para archivos de secretos (docker secrets)

        returns:
            tupla ordenada de fuentes de configuración las fuentes al inicio
            tienen mayor prioridad y sobrescriben valores de fuentes posteriores
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
