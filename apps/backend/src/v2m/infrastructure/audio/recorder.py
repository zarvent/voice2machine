# This file is part of voice2machine.
#
# voice2machine is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# voice2machine is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with voice2machine.  If not, see <https://www.gnu.org/licenses/>.

import threading
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from v2m.core.logging import logger
from v2m.domain.errors import RecordingError


class AudioRecorder:
    """
    CLASE RESPONSABLE DE LA GRABACIÓN DE AUDIO UTILIZANDO `SOUNDDEVICE`

    maneja el flujo de entrada de audio almacena los frames en un buffer
    pre-allocado y permite detener la grabación devolviendo los datos como
    un array de numpy con zero-copy cuando es posible

    OPTIMIZACIONES
    - buffer pre-allocado para evitar reallocaciones
    - zero-copy slice al detener
    - dtype float32 consistente
    """
    # tamaño del chunk en samples coincide con sounddevice default ~1024
    CHUNK_SIZE = 1024

    def __init__(self, sample_rate: int = 16000, channels: int = 1, max_duration_sec: int = 600, device_index: int | None = None):
        """
        INICIALIZA EL GRABADOR DE AUDIO CON BUFFER PRE-ALLOCADO

        ARGS:
            sample_rate: frecuencia de muestreo en hz
            channels: número de canales de audio
            max_duration_sec: duración máxima de grabación en segundos default 10 min
            device_index: índice del dispositivo de audio a usar
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_index = device_index
        self._recording = False
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()

        # buffer pre-allocado para evitar reallocaciones durante grabación
        # esto elimina el overhead de np.concatenate era O(n²) ahora O(1)
        self.max_samples = max_duration_sec * sample_rate

        # soporte para buffer multicanal
        if self.channels > 1:
            self._buffer: np.ndarray = np.zeros((self.max_samples, self.channels), dtype=np.float32)
        else:
            self._buffer: np.ndarray = np.zeros(self.max_samples, dtype=np.float32)

        self._write_pos = 0

    def start(self):
        """
        INICIA LA GRABACIÓN DE AUDIO EN UN HILO DE FONDO CALLBACK

        RAISES:
            RecordingError: si la grabación ya está en progreso o falla al iniciar el stream
        """
        if self._recording:
            raise RecordingError("grabación ya en progreso")

        self._recording = True
        self._write_pos = 0  # reiniciar posición del buffer

        def callback(indata: np.ndarray, frames: int, time, status):
            if status:
                logger.warning(f"estado de la grabación de audio {status}")

            with self._lock:
                if not self._recording:
                    return

                # calcular cuántos samples podemos escribir
                samples_to_write = min(frames, self.max_samples - self._write_pos)

                if samples_to_write > 0:
                    # escritura zero-copy al buffer pre-allocado flatten inline
                    end_pos = self._write_pos + samples_to_write

                    if self.channels > 1:
                        self._buffer[self._write_pos:end_pos, :] = indata[:samples_to_write, :]
                    else:
                        # indata es frames 1 o frames channels queremos 1d para buffer mono
                        # si indata tiene más columnas pero queremos mono tomamos el canal 0
                        # si indata es n 1 lo aplanamos o cortamos
                        # indata[:samples_to_write 0] da un corte 1d
                        self._buffer[self._write_pos:end_pos] = indata[:samples_to_write, 0]

                    self._write_pos = end_pos

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=callback,
                dtype="float32",
                device=self.device_index,
                blocksize=self.CHUNK_SIZE  # consistente para menor latencia
            )
            self._stream.start()
            logger.info("grabación de audio iniciada")
        except Exception as e:
            self._recording = False
            if self._stream:
                self._stream.close()
                self._stream = None
            raise RecordingError(f"falló al iniciar la grabación {e}") from e

    def stop(self, save_path: Path | None = None, return_data: bool = True) -> np.ndarray:
        """
        DETIENE LA GRABACIÓN Y DEVUELVE EL AUDIO CAPTURADO

        ARGS:
            save_path: ruta opcional para guardar el audio como archivo wav
            return_data: si es True retorna una copia del audio grabado default True
                         si es False retorna un array vacío ahorrando memoria

        RETURNS:
            el audio grabado como un array de numpy float32
            nota retorna una copia del buffer para evitar corrupción de datos

        RAISES:
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

        # usar vista (view) del buffer para operaciones intermedias sin copia
        if self.channels > 1:
            audio_view = self._buffer[:recorded_samples, :]
        else:
            audio_view = self._buffer[:recorded_samples]

        if save_path:
            # convertir float32 a int16 para wav usando la vista para evitar copia intermedia
            # OPTIMIZACIÓN: usamos audio_view directamente como fuente
            audio_int16 = (audio_view * 32767).astype(np.int16)
            with wave.open(str(save_path), 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16 bit
                wf.setframerate(self.sample_rate)
                # si channels > 1 audio es 2d samples channels
                # wave.writeframes espera bytes intercalados
                # tobytes en array 2d c-contiguous da bytes row-major
                # row0_col0 row0_col1 row1_col0 row1_col1...
                # esto es exactamente lo que pcm intercalado espera l r l r...
                wf.writeframes(audio_int16.tobytes())

        if not return_data:
             if self.channels > 1:
                 return np.array([], dtype=np.float32).reshape(0, self.channels)
             return np.array([], dtype=np.float32)

        # zero-copy slice retorna vista del buffer no copia
        # importante el caller debe procesar antes de la próxima grabación
        # retornamos una copia para evitar corrupción de datos si se reinicia la grabación
        return audio_view.copy()
