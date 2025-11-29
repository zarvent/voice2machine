import sounddevice as sd
import numpy as np
import threading
import wave
from pathlib import Path
from typing import Optional, List
from v2m.core.logging import logger
from v2m.domain.errors import RecordingError

class AudioRecorder:
    """
    clase responsable de la grabacion de audio utilizando `sounddevice`.

    maneja el flujo de entrada de audio, almacena los frames en memoria y
    permite detener la grabacion devolviendo los datos como un array de numpy.
    """
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """
        inicializa el grabador de audio.

        args:
            sample_rate (int): frecuencia de muestreo en hz.
            channels (int): numero de canales de audio.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self._recording = False
        self._frames: List[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        # duracion maxima para evitar oom 10 minutos
        self.max_samples = 10 * 60 * sample_rate
        self.current_samples = 0

    def start(self):
        """
        inicia la grabacion de audio en un hilo de fondo (callback).

        raises:
            RecordingError: si la grabacion ya esta en progreso o falla al iniciar el stream.
        """
        if self._recording:
            raise RecordingError("grabación ya en progreso")

        self._recording = True
        self._frames = []
        self.current_samples = 0

        def callback(indata, frames, time, status):
            if status:
                logger.warning(f"estado de la grabación de audio {status}")
            with self._lock:
                if self._recording:
                    if self.current_samples < self.max_samples:
                        self._frames.append(indata.copy())
                        self.current_samples += frames
                    else:
                        # detener la grabación si se alcanza la duración máxima (o simplemente dejar de añadir)
                        pass

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=callback,
                dtype="float32"
            )
            self._stream.start()
            logger.info("grabación de audio iniciada")
        except Exception as e:
            self._recording = False
            raise RecordingError(f"falló al iniciar la grabación {e}") from e

    def stop(self, save_path: Optional[Path] = None) -> np.ndarray:
        """
        detiene la grabacion y devuelve el audio capturado.

        args:
            save_path (Optional[Path]): ruta opcional para guardar el audio como archivo wav.

        returns:
            np.ndarray: el audio grabado como un array de numpy (float32).

        raises:
            RecordingError: si no hay una grabacion en curso.
        """
        if not self._recording:
            # si los fotogramas están vacíos y no se está grabando entonces no ha pasado nada
            if not self._frames and not self._stream:
                raise RecordingError("no hay grabación en curso")

        with self._lock:
            self._recording = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        logger.info("grabación de audio detenida")

        if not self._frames:
            return np.array([], dtype=np.float32)

        audio = np.concatenate(self._frames, axis=0).flatten()
        self._frames = [] # limpiar buffer para evitar devolver audio antiguo en llamadas subsecuentes

        if save_path:
            # convertir float32 a int16 para wav
            audio_int16 = (audio * 32767).astype(np.int16)
            with wave.open(str(save_path), 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2) # 16 bit
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_int16.tobytes())

        return audio
