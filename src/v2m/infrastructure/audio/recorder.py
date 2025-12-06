# This file is part of voice2machine.
#
# voice2machine is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import sounddevice as sd
import numpy as np
import threading
import wave
from pathlib import Path
from typing import Optional
from v2m.core.logging import logger
from v2m.domain.errors import RecordingError

class AudioRecorder:
    """
    clase responsable de la grabación de audio utilizando `sounddevice`

    maneja el flujo de entrada de audio almacena los frames en un buffer
    pre-allocado y permite detener la grabación devolviendo los datos como
    un array de numpy con zero-copy cuando es posible

    optimizaciones
    - buffer pre-allocado para evitar reallocaciones
    - zero-copy slice al detener
    - dtype float32 consistente
    """
    # Tamaño del chunk en samples (match con sounddevice default ~1024)
    CHUNK_SIZE = 1024

    def __init__(self, sample_rate: int = 16000, channels: int = 1, max_duration_sec: int = 600, device_index: Optional[int] = None):
        """
        inicializa el grabador de audio con buffer pre-allocado

        args:
            sample_rate: frecuencia de muestreo en hz
            channels: número de canales de audio
            max_duration_sec: duración máxima de grabación en segundos (default 10 min)
            device_index: índice del dispositivo de audio a usar
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_index = device_index
        self._recording = False
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()

        # Buffer pre-allocado para evitar reallocaciones durante grabación
        # Esto elimina el overhead de np.concatenate (era O(n²), ahora O(1))
        self.max_samples = max_duration_sec * sample_rate

        # FIX: Support multi-channel buffer
        if self.channels > 1:
            self._buffer: np.ndarray = np.zeros((self.max_samples, self.channels), dtype=np.float32)
        else:
            self._buffer: np.ndarray = np.zeros(self.max_samples, dtype=np.float32)

        self._write_pos = 0

    def start(self):
        """
        inicia la grabación de audio en un hilo de fondo (callback)

        raises:
            RecordingError: si la grabación ya está en progreso o falla al iniciar el stream
        """
        if self._recording:
            raise RecordingError("grabación ya en progreso")

        self._recording = True
        self._write_pos = 0  # Reset buffer position

        def callback(indata: np.ndarray, frames: int, time, status):
            if status:
                logger.warning(f"estado de la grabación de audio {status}")

            with self._lock:
                if not self._recording:
                    return

                # Calcular cuántos samples podemos escribir
                samples_to_write = min(frames, self.max_samples - self._write_pos)

                if samples_to_write > 0:
                    # Zero-copy write al buffer pre-allocado (flatten inline)
                    end_pos = self._write_pos + samples_to_write

                    if self.channels > 1:
                        self._buffer[self._write_pos:end_pos, :] = indata[:samples_to_write, :]
                    else:
                        # indata is (frames, 1) or (frames, channels), we want 1D for mono buffer
                        # if indata has more columns but we want mono, we take channel 0.
                        # if indata is (N, 1), we flatten it or slice.
                        # indata[:samples_to_write, 0] gives 1D slice.
                        self._buffer[self._write_pos:end_pos] = indata[:samples_to_write, 0]

                    self._write_pos = end_pos

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=callback,
                dtype="float32",
                device=self.device_index,
                blocksize=self.CHUNK_SIZE  # Consistente para menor latencia
            )
            self._stream.start()
            logger.info("grabación de audio iniciada")
        except Exception as e:
            self._recording = False
            if self._stream:
                self._stream.close()
                self._stream = None
            raise RecordingError(f"falló al iniciar la grabación {e}") from e

    def stop(self, save_path: Optional[Path] = None) -> np.ndarray:
        """
        detiene la grabación y devuelve el audio capturado

        args:
            save_path: ruta opcional para guardar el audio como archivo wav

        returns:
            el audio grabado como un array de numpy (float32)
            nota: retorna una copia del buffer para evitar corrupción de datos

        raises:
            RecordingError: si no hay una grabación en curso
        """
        if not self._recording:
            raise RecordingError("no hay grabación en curso")

        with self._lock:
            self._recording = False
            recorded_samples = self._write_pos

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        logger.info(f"grabación de audio detenida ({recorded_samples} samples)")

        if recorded_samples == 0:
            if self.channels > 1:
                 return np.array([], dtype=np.float32).reshape(0, self.channels)
            return np.array([], dtype=np.float32)

        # Zero-copy slice - retorna vista del buffer, no copia
        # IMPORTANTE: el caller debe procesar antes de la próxima grabación
        # FIX: Retornamos una copia para evitar corrupción de datos si se reinicia la grabación
        if self.channels > 1:
            audio = self._buffer[:recorded_samples, :].copy()
        else:
            audio = self._buffer[:recorded_samples].copy()

        if save_path:
            # convertir float32 a int16 para wav (esto sí hace copia)
            audio_int16 = (audio * 32767).astype(np.int16)
            with wave.open(str(save_path), 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16 bit
                wf.setframerate(self.sample_rate)
                # If channels > 1, audio is 2D (samples, channels).
                # wave.writeframes expects interleaved bytes.
                # tobytes() on C-contiguous 2D array gives row-major bytes:
                # row0_col0, row0_col1, row1_col0, row1_col1...
                # This is exactly what interleaved PCM expects (L, R, L, R...).
                wf.writeframes(audio_int16.tobytes())

        return audio
