"""
módulo para la carga y gestión de la configuración de la aplicación utilizando pydantic settings
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
    configuracion de rutas de archivos y directorios para la aplicacion.

    atributos:
        recording_flag (Path): ruta al archivo de bandera de grabacion.
        audio_file (Path): ruta al archivo de audio temporal.
        log_file (Path): ruta al archivo de registro de depuracion.
        venv_path (Path): ruta al entorno virtual de python.
    """
    recording_flag: Path = Field(default=Path("/tmp/v2m_recording.pid"))
    audio_file: Path = Field(default=Path("/tmp/v2m_audio.wav"))
    log_file: Path = Field(default=Path("/tmp/v2m_debug.log"))
    venv_path: Path = Field(default=Path("~/v2m/venv"))

    def __getitem__(self, item):
        return getattr(self, item)

class VadParametersConfig(BaseModel):
    """
    configuracion de parametros para la deteccion de actividad de voz (vad).

    atributos:
        threshold (float): umbral de probabilidad para detectar voz.
        min_speech_duration_ms (int): duracion minima del habla en milisegundos.
        min_silence_duration_ms (int): duracion minima del silencio en milisegundos.
    """
    threshold: float = 0.5
    min_speech_duration_ms: int = 250
    min_silence_duration_ms: int = 500

    def __getitem__(self, item):
        return getattr(self, item)

class WhisperConfig(BaseModel):
    """
    configuracion para el modelo de transcripcion whisper.

    atributos:
        model (str): nombre del modelo whisper a utilizar (ej. large-v2).
        language (str): codigo de idioma para la transcripcion (ej. es).
        device (str): dispositivo de computo a utilizar (ej. cuda, cpu).
        compute_type (str): tipo de computo para la precision (ej. float16).
        device_index (int): indice del dispositivo gpu.
        num_workers (int): numero de trabajadores para el procesamiento.
        beam_size (int): tamano del beam search para la decodificacion.
        best_of (int): numero de candidatos a considerar.
        temperature (float): temperatura para el muestreo.
        vad_filter (bool): si se debe aplicar filtro vad.
        vad_parameters (VadParametersConfig): configuracion detallada del vad.
    """
    model: str = "large-v2"
    language: str = "es"
    device: str = "cuda"
    compute_type: str = "float16"
    device_index: int = 0
    num_workers: int = 4
    beam_size: int = 5
    best_of: int = 5
    temperature: float = 0.0
    vad_filter: bool = True
    vad_parameters: VadParametersConfig = Field(default_factory=VadParametersConfig)

    def __getitem__(self, item):
        return getattr(self, item)

class GeminiConfig(BaseModel):
    """
    configuracion para el servicio de llm gemini.

    atributos:
        model (str): identificador del modelo gemini.
        temperature (float): temperatura para la generacion de texto.
        max_tokens (int): numero maximo de tokens a generar.
        max_input_chars (int): numero maximo de caracteres de entrada.
        request_timeout (int): tiempo de espera maximo para la solicitud.
        retry_attempts (int): numero de intentos de reintento.
        retry_min_wait (int): tiempo minimo de espera entre reintentos.
        retry_max_wait (int): tiempo maximo de espera entre reintentos.
        api_key (Optional[str]): clave de api para autenticacion.
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
    """
    clase principal de configuracion que agrupa todas las configuraciones.

    atributos:
        paths (PathsConfig): configuracion de rutas.
        whisper (WhisperConfig): configuracion de whisper.
        gemini (GeminiConfig): configuracion de gemini.
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
        """
        personaliza las fuentes de configuracion para incluir archivos toml.

        args:
            settings_cls (Type[BaseSettings]): clase de configuracion.
            init_settings (PydanticBaseSettingsSource): configuracion inicial.
            env_settings (PydanticBaseSettingsSource): configuracion de variables de entorno.
            dotenv_settings (PydanticBaseSettingsSource): configuracion de archivo .env.
            file_secret_settings (PydanticBaseSettingsSource): configuracion de secretos.

        returns:
            Tuple[PydanticBaseSettingsSource, ...]: tupla de fuentes de configuracion ordenadas.
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
