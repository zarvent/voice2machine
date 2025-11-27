import torch
import numpy as np
from typing import List, Optional
import threading
from v2m.core.logging import logger

class VADService:
    """
    servicio para la deteccion de actividad de voz (vad) utilizando silero vad.

    permite truncar los silencios del audio antes de enviarlo a whisper,
    mejorando la eficiencia y reduciendo el tiempo de inferencia.
    """
    def __init__(self):
        self.model = None
        self.utils = None
        self.get_speech_timestamps = None
        self.disabled = False  # si falla la carga, saltar VAD

    def load_model(self, timeout_sec: float = 10.0):
        """
        carga el modelo silero vad de forma perezosa con timeout.

        para evitar bloqueos por descargas de internet, se aplica un timeout. si
        vence el tiempo, se deshabilita vad para esta sesion y se continua sin vad.

        args:
            timeout_sec (float): tiempo maximo de espera en segundos.
        """
        if self.disabled:
            return
        if self.model is not None:
            return

        logger.info("cargando modelo silero vad...")

        exc_holder: list[Exception] = []

        def _do_load():
            try:
                self.model, self.utils = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    force_reload=False,
                    onnx=False
                )
            except Exception as e:  # capturar y propagar después
                exc_holder.append(e)

        t = threading.Thread(target=_do_load, daemon=True)
        t.start()
        t.join(timeout=timeout_sec)

        if t.is_alive():
            # aún cargando (probablemente descarga). deshabilitar VAD para no bloquear.
            self.disabled = True
            logger.warning("timeout cargando silero VAD; VAD deshabilitado para esta sesión")
            return

        if exc_holder:
            self.disabled = True
            logger.error(f"error al cargar silero vad {exc_holder[0]}")
            raise exc_holder[0]

        (self.get_speech_timestamps, _, _, _, _) = self.utils
        logger.info("modelo silero vad cargado")

    def process(self, audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """
        procesa el audio y elimina los segmentos de silencio.

        args:
            audio (np.ndarray): array de numpy con el audio (float32).
            sample_rate (int): frecuencia de muestreo (debe ser 8000 o 16000 para silero).

        returns:
            np.ndarray: un nuevo array de numpy que contiene solo los segmentos de voz concatenados.
            si no se detecta voz devuelve un array vacio.
        """
        # si el audio está vacío, retornar de inmediato
        if audio.size == 0:
            return np.array([], dtype=np.float32)

        try:
            self.load_model()
        except Exception:
            # si falla la carga del modelo, continuar con el audio original
            logger.warning("VAD no disponible, se usará audio sin truncar")
            return audio

        if self.disabled or self.model is None or self.get_speech_timestamps is None:
            # VAD deshabilitado o no disponible
            return audio

        # convertir numpy array a tensor de torch
        # silero espera un tensor de forma (1 N) o (N)
        audio_tensor = torch.from_numpy(audio)

        # obtener timestamps de voz
        # threshold umbral de probabilidad de voz (0.5 es default)
        timestamps = self.get_speech_timestamps(
            audio_tensor,
            self.model,
            sampling_rate=sample_rate,
            threshold=0.5
        )

        if not timestamps:
            logger.info("VAD no se detectó voz")
            return np.array([], dtype=np.float32)

        # concatenar los chunks de voz
        speech_chunks = []
        for ts in timestamps:
            start = int(ts['start'])
            end = int(ts['end'])
            speech_chunks.append(audio[start:end])

        if not speech_chunks:
            return np.array([], dtype=np.float32)

        result = np.concatenate(speech_chunks)

        original_duration = len(audio) / sample_rate
        new_duration = len(result) / sample_rate
        logger.info(f"VAD audio truncado de {original_duration:.2f}s a {new_duration:.2f}s")

        return result
