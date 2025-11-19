import torch
import numpy as np
from typing import List, Optional
from whisper_dictation.core.logging import logger

class VADService:
    """
    Servicio para la detección de actividad de voz (VAD) utilizando Silero VAD.

    Permite truncar los silencios del audio antes de enviarlo a Whisper,
    mejorando la eficiencia y reduciendo el tiempo de inferencia.
    """
    def __init__(self):
        self.model = None
        self.utils = None
        self.get_speech_timestamps = None

    def load_model(self):
        """
        Carga el modelo Silero VAD de forma perezosa.
        """
        if self.model is None:
            logger.info("Cargando modelo Silero VAD...")
            try:
                # Usamos torch.hub para cargar el modelo desde el repositorio oficial
                # force_reload=False usa la caché local si existe
                self.model, self.utils = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    force_reload=False,
                    onnx=False # Usamos PyTorch por defecto ya que instalamos torch
                )
                (self.get_speech_timestamps, _, _, _, _) = self.utils
                logger.info("Modelo Silero VAD cargado.")
            except Exception as e:
                logger.error(f"Error al cargar Silero VAD: {e}")
                raise e

    def process(self, audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """
        Procesa el audio y elimina los segmentos de silencio.

        Args:
            audio: Array de numpy con el audio (float32).
            sample_rate: Frecuencia de muestreo (debe ser 8000 o 16000 para Silero).

        Returns:
            Un nuevo array de numpy que contiene solo los segmentos de voz concatenados.
            Si no se detecta voz, devuelve un array vacío.
        """
        self.load_model()

        # Convertir numpy array a tensor de torch
        # Silero espera un tensor de forma (1, N) o (N)
        audio_tensor = torch.from_numpy(audio)

        # Obtener timestamps de voz
        # threshold: umbral de probabilidad de voz (0.5 es default)
        timestamps = self.get_speech_timestamps(
            audio_tensor,
            self.model,
            sampling_rate=sample_rate,
            threshold=0.5
        )

        if not timestamps:
            logger.info("VAD: No se detectó voz.")
            return np.array([], dtype=np.float32)

        # Concatenar los chunks de voz
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
        logger.info(f"VAD: Audio truncado de {original_duration:.2f}s a {new_duration:.2f}s")

        return result
