"""
Módulo que implementa el servicio de transcripción utilizando `faster-whisper`.

Esta es la implementación concreta de la interfaz `TranscriptionService`. Se encarga
de la lógica de bajo nivel para:
-   Gestionar el proceso de grabación de audio usando `AudioRecorder`.
-   Cargar el modelo de WHISPER.
-   Realizar la transcripción del audio grabado directamente desde la memoria.
"""

from typing import Optional
from faster_whisper import WhisperModel
from whisper_dictation.application.transcription_service import TranscriptionService
from whisper_dictation.config import config
from whisper_dictation.domain.errors import RecordingError
from whisper_dictation.core.logging import logger
from whisper_dictation.infrastructure.audio.recorder import AudioRecorder
from whisper_dictation.infrastructure.vad_service import VADService

class WhisperTranscriptionService(TranscriptionService):
    """
    Implementación del `TranscriptionService` que usa `faster-whisper` y `AudioRecorder`.
    """
    def __init__(self, vad_service: Optional[VADService] = None) -> None:
        """
        Inicializa el servicio de transcripción.

        No carga el modelo de WHISPER en este punto para acelerar el inicio de la aplicación.

        Args:
            vad_service: Servicio opcional para truncado de silencios.
        """
        self._model: Optional[WhisperModel] = None
        self.recorder = AudioRecorder()
        self.vad_service = vad_service

    @property
    def model(self) -> WhisperModel:
        """
        Carga el modelo de `faster-whisper` de forma perezosa (lazy loading).

        El modelo solo se carga en memoria la primera vez que se accede a esta
        propiedad. Esto evita un consumo de recursos innecesario si solo se
        inicia la grabación sin completarla.

        Returns:
            La instancia del modelo de WHISPER cargado.
        """
        if self._model == None:
            logger.info("cargando modelo de WHISPER...")
            whisper_config = config.whisper
            self._model = WhisperModel(
                whisper_config.model,
                device=whisper_config.device,
                compute_type=whisper_config.compute_type,
                device_index=whisper_config.device_index,
                num_workers=whisper_config.num_workers
            )
            logger.info("modelo de WHISPER cargado")
        return self._model

    def start_recording(self) -> None:
        """
        Inicia la grabación de audio.

        Utiliza `AudioRecorder` para capturar audio en un hilo separado.

        Raises:
            RecordingError: Si ya hay una grabación en proceso o falla el inicio.
        """
        try:
            self.recorder.start()
            logger.info("grabación iniciada")
        except RecordingError as e:
            logger.error(f"Error al iniciar grabación: {e}")
            raise e

    def stop_and_transcribe(self) -> str:
        """
        Detiene la grabación y transcribe el audio.

        Realiza los siguientes pasos:
        1.  Detiene el `AudioRecorder` y obtiene los datos de audio en memoria (numpy array).
        2.  Aplica VAD (Smart Truncation) si está disponible.
        3.  Verifica que se haya grabado audio válido.
        4.  Utiliza el modelo de WHISPER para transcribir el audio directamente desde memoria.

        Returns:
            El texto transcrito.

        Raises:
            RecordingError: Si no hay una grabación activa o si el audio es inválido.
        """
        try:
            # Detener grabación y obtener audio (sin guardar a disco)
            audio_data = self.recorder.stop()
        except RecordingError as e:
            logger.error(f"Error al detener grabación: {e}")
            raise e

        if audio_data.size == 0:
            raise RecordingError("no se grabó audio o el buffer está vacío")

        # --- Aplicar VAD (Smart Truncation) ---
        if self.vad_service:
            try:
                audio_data = self.vad_service.process(audio_data)
                if audio_data.size == 0:
                    logger.warning("VAD eliminó todo el audio (solo silencio detectado)")
                    # Podríamos lanzar error o retornar string vacío
                    return ""
            except Exception as e:
                logger.error(f"Fallo en VAD, usando audio original: {e}")

        # --- transcripción con whisper ---
        logger.info("transcribiendo audio...")
        whisper_config = config.whisper

        # faster-whisper acepta numpy array directamente
        segments, _ = self.model.transcribe(
            audio_data,
            language=whisper_config.language,
            beam_size=whisper_config.beam_size,
            best_of=whisper_config.best_of,
            temperature=whisper_config.temperature,
            vad_filter=whisper_config.vad_filter,
            vad_parameters=whisper_config.vad_parameters.model_dump()
        )
        text = " ".join([segment.text.strip() for segment in segments])
        logger.info("transcripción completada")

        return text
