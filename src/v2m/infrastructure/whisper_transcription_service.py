"""
módulo que implementa el servicio de transcripción utilizando `faster-whisper`

esta es la implementación concreta de la interfaz `transcriptionservice` se encarga
de la lógica de bajo nivel para
-   gestionar el proceso de grabación de audio usando `audiorecorder`
-   cargar el modelo de WHISPER
-   realizar la transcripción del audio grabado directamente desde la memoria
"""

from typing import Optional
from faster_whisper import WhisperModel
from v2m.application.transcription_service import TranscriptionService
from v2m.config import config
from v2m.domain.errors import RecordingError
from v2m.core.logging import logger
from v2m.infrastructure.audio.recorder import AudioRecorder
from v2m.infrastructure.vad_service import VADService

class WhisperTranscriptionService(TranscriptionService):
    """
    implementación del `transcriptionservice` que usa `faster-whisper` y `audiorecorder`
    """
    def __init__(self, vad_service: Optional[VADService] = None) -> None:
        """
        inicializa el servicio de transcripción

        no carga el modelo de WHISPER en este punto para acelerar el inicio de la aplicación

        args:
            vad_service: servicio opcional para truncado de silencios
        """
        self._model: Optional[WhisperModel] = None
        self.recorder = AudioRecorder()
        self.vad_service = vad_service

    @property
    def model(self) -> WhisperModel:
        """
        carga el modelo de `faster-whisper` de forma perezosa (lazy loading)

        el modelo solo se carga en memoria la primera vez que se accede a esta
        propiedad esto evita un consumo de recursos innecesario si solo se
        inicia la grabación sin completarla

        returns:
            la instancia del modelo de WHISPER cargado
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
        inicia la grabación de audio

        utiliza `audiorecorder` para capturar audio en un hilo separado

        raises:
            recordingerror: si ya hay una grabación en proceso o falla el inicio
        """
        try:
            self.recorder.start()
            logger.info("grabación iniciada")
        except RecordingError as e:
            logger.error(f"error al iniciar grabación {e}")
            raise e

    def stop_and_transcribe(self) -> str:
        """
        detiene la grabación y transcribe el audio

        realiza los siguientes pasos
        1.  detiene el `audiorecorder` y obtiene los datos de audio en memoria (numpy array)
        2.  aplica vad (smart truncation) si está disponible
        3.  verifica que se haya grabado audio válido
        4.  utiliza el modelo de WHISPER para transcribir el audio directamente desde memoria

        returns:
            el texto transcrito

        raises:
            recordingerror: si no hay una grabación activa o si el audio es inválido
        """
        try:
            # detener grabación y obtener audio (sin guardar a disco)
            audio_data = self.recorder.stop()
        except RecordingError as e:
            logger.error(f"error al detener grabación {e}")
            raise e

        if audio_data.size == 0:
            raise RecordingError("no se grabó audio o el buffer está vacío")

        # --- aplicar vad (smart truncation) ---
        if self.vad_service:
            try:
                audio_data = self.vad_service.process(audio_data)
                if audio_data.size == 0:
                    logger.warning("VAD eliminó todo el audio (solo silencio detectado)")
                    # podríamos lanzar error o retornar string vacío
                    return ""
            except Exception as e:
                logger.error(f"fallo en VAD usando audio original {e}")

        # --- transcripción con WHISPER ---
        logger.info("transcribiendo audio...")
        whisper_config = config.whisper

        # 1 lógica para auto-detección
        lang = whisper_config.language
        if lang == "auto":
            lang = None  # none activa la detección automática en faster-whisper

        # 2 prompt inicial (optimización bilingüe)
        # esto le dice al modelo "oye el audio será en español o inglés"
        # ayuda mucho con audios cortos que podrían confundirse
        bilingual_prompt = "esta es una transcripción en español this is also in english"

        # faster-whisper acepta numpy array directamente
        segments, info = self.model.transcribe(
            audio_data,
            language=lang,
            task="transcribe",  # <--- bloquea la traducción
            initial_prompt=bilingual_prompt,  # <--- inyección de contexto
            beam_size=whisper_config.beam_size,
            best_of=whisper_config.best_of,
            temperature=whisper_config.temperature,
            vad_filter=whisper_config.vad_filter,
            vad_parameters=whisper_config.vad_parameters.model_dump()
        )

        # si es detección automática podemos loguear qué idioma detectó
        if lang is None:
            logger.info(f"idioma detectado {info.language} (prob {info.language_probability:.2f})")

        text = " ".join([segment.text.strip() for segment in segments])
        logger.info("transcripción completada")

        return text
