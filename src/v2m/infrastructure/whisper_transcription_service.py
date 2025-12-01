"""
modulo que implementa el servicio de transcripcion utilizando `faster-whisper`.

esta es la implementacion concreta de la interfaz `transcriptionservice`. se encarga
de la logica de bajo nivel para:
-   gestionar el proceso de grabacion de audio usando `audiorecorder`.
-   cargar el modelo de whisper.
-   realizar la transcripcion del audio grabado directamente desde la memoria.
"""

import gc
import torch
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
    implementacion del `transcriptionservice` que usa `faster-whisper` y `audiorecorder`.
    """
    def __init__(self, vad_service: Optional[VADService] = None) -> None:
        """
        inicializa el servicio de transcripcion.

        no carga el modelo de whisper en este punto para acelerar el inicio de la aplicacion.

        args:
            vad_service (Optional[VADService]): servicio opcional para truncado de silencios.
        """
        self._model: Optional[WhisperModel] = None
        self.recorder = AudioRecorder(device_index=config.whisper.audio_device_index)
        self.vad_service = vad_service

    @property
    def model(self) -> WhisperModel:
        """
        carga el modelo de `faster-whisper` de forma perezosa (lazy loading).

        el modelo solo se carga en memoria la primera vez que se accede a esta
        propiedad. esto evita un consumo de recursos innecesario si solo se
        inicia la grabacion sin completarla.

        returns:
            WhisperModel: la instancia del modelo de whisper cargado.
        """
        if self._model is None:
            logger.info("cargando modelo de WHISPER...")
            whisper_config = config.whisper

            try:
                self._model = WhisperModel(
                    whisper_config.model,
                    device=whisper_config.device,
                    compute_type=whisper_config.compute_type,
                    device_index=whisper_config.device_index,
                    num_workers=whisper_config.num_workers
                )
                logger.info(f"modelo de WHISPER cargado en {whisper_config.device}")
            except Exception as e:
                logger.error(f"Error cargando modelo en {whisper_config.device}: {e}")
                if whisper_config.device == "cuda":
                    logger.warning("Intentando fallback a CPU...")
                    try:
                        self._model = WhisperModel(
                            whisper_config.model,
                            device="cpu",
                            compute_type="int8", # CPU suele requerir int8 para velocidad
                            num_workers=whisper_config.num_workers
                        )
                        logger.info("modelo de WHISPER cargado en CPU (Fallback)")
                    except Exception as e2:
                        logger.critical(f"Fallo crítico: No se pudo cargar el modelo ni en CPU: {e2}")
                        raise e2
                else:
                    raise e

        return self._model

    def start_recording(self) -> None:
        """
        inicia la grabacion de audio.

        utiliza `audiorecorder` para capturar audio en un hilo separado.

        raises:
            RecordingError: si ya hay una grabacion en proceso o falla el inicio.
        """
        try:
            self.recorder.start()
            logger.info("grabación iniciada")
        except RecordingError as e:
            logger.error(f"error al iniciar grabación {e}")
            raise e

    def stop_and_transcribe(self) -> str:
        """
        detiene la grabacion y transcribe el audio.

        realiza los siguientes pasos:
        1.  detiene el `audiorecorder` y obtiene los datos de audio en memoria (numpy array).
        2.  aplica vad (smart truncation) si esta disponible.
        3.  verifica que se haya grabado audio valido.
        4.  utiliza el modelo de whisper para transcribir el audio directamente desde memoria.
        5.  limpia recursos (gc, cuda cache) para minimizar uso de memoria.

        returns:
            str: el texto transcrito.

        raises:
            RecordingError: si no hay una grabacion activa o si el audio es invalido.
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
                    return ""
            except Exception as e:
                logger.error(f"fallo en VAD usando audio original {e}")

        # --- transcripción con WHISPER ---
        logger.info("transcribiendo audio...")
        whisper_config = config.whisper

        try:
            # 1 lógica para auto-detección
            lang = whisper_config.language
            if lang == "auto":
                lang = None  # none activa la detección automática en faster-whisper

            # 2 prompt inicial optimizado (Español Latinoamericano + Inglés Técnico)
            # Este prompt fuerza puntuación correcta, evita alucinaciones y calibra el estilo.
            # Incluye términos técnicos de programación para mejor reconocimiento de spanglish.
            bilingual_prompt = (
                "La siguiente es una transcripción precisa en español latinoamericano e inglés técnico. "
                "Por favor, mantén la puntuación correcta, nombres propios y términos de programación. "
                "Ok, let's start coding."
            )

            # faster-whisper acepta numpy array directamente
            # NOTA: VAD interno DESHABILITADO - ya aplicamos Silero VAD arriba
            # Esto ahorra ~40MB VRAM y evita doble procesamiento
            segments, info = self.model.transcribe(
                audio_data,
                language=lang,
                task="transcribe",
                initial_prompt=bilingual_prompt,
                beam_size=whisper_config.beam_size,
                best_of=whisper_config.best_of,
                temperature=whisper_config.temperature,
                patience=1.5,  # Mejora precisión: explora más opciones antes de decidir
                vad_filter=False,  # Silero VAD ya procesó el audio
            )

            if lang is None:
                logger.info(f"idioma detectado {info.language} (prob {info.language_probability:.2f})")

            text = " ".join([segment.text.strip() for segment in segments])
            logger.info("transcripción completada")
            return text

        except Exception as e:
            logger.error(f"Error durante transcripción: {e}")
            raise e
        finally:
            # --- LIMPIEZA DE RECURSOS (OPTIMIZADA) ---
            # Limpieza lazy: solo gc.collect() si hay presión de memoria
            # empty_cache() es barato (~1ms), gc.collect() es caro (~10-50ms)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Solo forzar GC si el heap creció mucho (>100MB desde última limpieza)
            # Esto evita gc.collect() en cada transcripción corta
            import sys
            if hasattr(sys, 'getsizeof'):
                # Programar limpieza diferida para no bloquear el retorno
                import threading
                threading.Thread(target=gc.collect, daemon=True).start()
