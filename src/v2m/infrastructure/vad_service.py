import torch
import numpy as np
from typing import List, Optional
from v2m.core.logging import logger

class VADService:
    """
    servicio para la detección de actividad de voz (VAD) utilizando silero vad

    permite truncar los silencios del audio antes de enviarlo a WHISPER
    mejorando la eficiencia y reduciendo el tiempo de inferencia
    """
    def __init__(self):
        self.model = None
        self.utils = None
        self.get_speech_timestamps = None

    def load_model(self):
        """
        carga el modelo silero vad de forma perezosa
        """
        if self.model is None:
            logger.info("cargando modelo silero vad...")
            try:
                # usamos torch.hub para cargar el modelo desde el repositorio oficial
                # force_reload=false usa la caché local si existe
                self.model, self.utils = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    force_reload=False,
                    onnx=False # usamos pytorch por defecto ya que instalamos torch
                )
                (self.get_speech_timestamps, _, _, _, _) = self.utils
                logger.info("modelo silero vad cargado")
            except Exception as e:
                logger.error(f"error al cargar silero vad {e}")
                raise e

    def process(self, audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """
        procesa el audio y elimina los segmentos de silencio

        args:
            audio: array de numpy con el audio (float32)
            sample_rate: frecuencia de muestreo (debe ser 8000 o 16000 para silero)

        returns:
            un nuevo array de numpy que contiene solo los segmentos de voz concatenados
            si no se detecta voz devuelve un array vacío
        """
        self.load_model()

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
