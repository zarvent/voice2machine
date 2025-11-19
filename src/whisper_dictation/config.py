"""
Módulo para la carga y gestión de la configuración de la aplicación utilizando Pydantic Settings.
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

# --- Ruta base del proyecto ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class PathsConfig(BaseModel):
    recording_flag: Path = Field(default=Path("/tmp/whisper_recording.pid"))
    audio_file: Path = Field(default=Path("/tmp/whisper_audio.wav"))
    log_file: Path = Field(default=Path("/tmp/whisper_debug.log"))
    venv_path: Path = Field(default=Path("~/whisper-dictation/venv"))

    def __getitem__(self, item):
        return getattr(self, item)

class VadParametersConfig(BaseModel):
    threshold: float = 0.5
    min_speech_duration_ms: int = 250
    min_silence_duration_ms: int = 500

    def __getitem__(self, item):
        return getattr(self, item)

class WhisperConfig(BaseModel):
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
