import asyncio
import threading
import wave
from multiprocessing import shared_memory
from pathlib import Path
from typing import Literal

import numpy as np

try:
    import sounddevice as sd
except OSError:
    sd = None

from v2m.shared.errors import RecordingError
from v2m.shared.logging import logger

# Intenta importar el motor de audio Rust
try:
    from v2m_engine import AudioRecorder as RustAudioRecorder
    from v2m_engine import ZeroCopyAudioRecorder as RustZeroCopyRecorder

    HAS_RUST_ENGINE = True
    HAS_ZERO_COPY = True
    logger.info("🚀 motor de audio rust v2m_engine cargado correctamente (zero-copy disponible)")
except ImportError:
    HAS_RUST_ENGINE = False
    HAS_ZERO_COPY = False
    logger.warning("⚠️ motor de audio rust no disponible usando fallback python")

# Alias para compatibilidad
RecorderMode = Literal["standard", "zero_copy", "fallback"]


class AudioRecorder:
    """Clase responsable de la grabación de audio.

    Implementa el patrón de fachada ("Strangler Fig") para modernizar el stack de audio,
    seleccionando automáticamente entre tres motores para garantizar estabilidad y rendimiento.

    Motores soportados (SOTA 2026):
    1. **Motor Zero-Copy (v2m_engine.ZeroCopyAudioRecorder)** - [Recomendado para streaming]
       - **Zero-Copy Bridge**: Audio almacenado en /dev/shm, accesible directamente por Python.
       - **Lock-Free**: Canal `flume` para notificaciones sin bloqueo del GIL.
       - **Atomic State**: Contadores atómicos para lectura no bloqueante.
       - Uso: `mode="zero_copy"` o detección automática.

    2. **Motor Rust Standard (v2m_engine.AudioRecorder)** - [Predeterminado]
       - **State of the Art (2026)**: Utiliza `cpal` + `ringbuf` (SPSC).
       - **Lock-Free**: El hilo de audio es 'Wait-Free', garantizando cero bloqueos (glitch-free).
       - **GIL-Free**: La captura ocurre fuera del Global Interpreter Lock de Python.
       - Uso: `mode="standard"` o detección automática.

    3. **Motor Python (sounddevice)** - [Fallback]
       - Se activa automáticamente si falla Rust (ej. hardware no soportado o error de driver).
       - Utiliza `sounddevice` (PortAudio wrapper) con buffers pre-allocados.
       - Uso: `mode="fallback"` o detección automática.

    Optimizaciones:
    - Buffer pre-allocado en modo fallback para evitar reallocaciones O(n) -> O(1).
    - Arquitectura resiliente: si Rust falla, el usuario no nota interrupción.
    - Zero-copy: `read_chunk_zero_copy()` retorna vista directa a /dev/shm sin copias.
    """

    # Tamaño del chunk en samples (coincide con sounddevice default ~1024)
    CHUNK_SIZE = 1024

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        max_duration_sec: int = 600,
        device_index: int | None = None,
        mode: RecorderMode = "zero_copy",
    ):
        """Inicializa el grabador de audio.

        Args:
            sample_rate: Frecuencia de muestreo en Hz.
            channels: Número de canales de audio.
            max_duration_sec: Duración máxima de grabación en segundos. Defecto: 10 min.
            device_index: Índice del dispositivo de audio a usar (solo soportado en modo Python).
            mode: Modo de grabación:
                - "zero_copy": Usa SharedMemory para transferencia sin copias (recomendado).
                - "standard": Usa el motor Rust estándar con ringbuf.
                - "fallback": Fuerza el uso del motor Python.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_index = device_index
        self._recording = False
        self._mode = mode

        # Estado para motores Rust
        self._rust_recorder: RustAudioRecorder | None = None
        self._zero_copy_recorder: RustZeroCopyRecorder | None = None
        self._shm: shared_memory.SharedMemory | None = None
        self._shm_name: str | None = None

        # Estado para el motor Python (fallback)
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._buffer: np.ndarray | None = None
        self._write_pos = 0
        self._last_read_pos = 0  # Para streaming con fallback Python
        self.max_samples = max_duration_sec * sample_rate

        # Selección de motor según modo solicitado
        if mode == "zero_copy" and HAS_ZERO_COPY and device_index is None:
            try:
                self._zero_copy_recorder = RustZeroCopyRecorder(sample_rate, channels, max_duration_sec)
                self._shm_name = self._zero_copy_recorder.get_shm_name()
                logger.debug(f"usando motor zero-copy rust (shm={self._shm_name})")
                return
            except Exception as e:
                logger.error(f"error inicializando motor zero-copy: {e} - intentando standard")

        if mode in ("zero_copy", "standard") and HAS_RUST_ENGINE and device_index is None:
            try:
                self._rust_recorder = RustAudioRecorder(sample_rate, channels)
                logger.debug("usando motor de grabación rust standard")
                return
            except Exception as e:
                logger.error(f"error inicializando motor rust: {e} - cayendo a python")

        if sd is None:
            logger.warning("sounddevice no está disponible (PortAudio no encontrado)")

        # Inicialización del fallback Python (buffer pre-allocado)
        self._buffer = self._allocate_buffer()

    def _allocate_buffer(self) -> np.ndarray:
        """Asigna un buffer pre-allocado basado en la configuración de canales."""
        if self.channels > 1:
            return np.zeros((self.max_samples, self.channels), dtype=np.float32)
        return np.zeros(self.max_samples, dtype=np.float32)

    def _empty_audio_array(self) -> np.ndarray:
        """Retorna un array de audio vacío con la forma correcta."""
        if self.channels > 1:
            return np.array([], dtype=np.float32).reshape(0, self.channels)
        return np.array([], dtype=np.float32)

    def supports_streaming(self) -> bool:
        """Indica si el modo actual soporta streaming eficiente.

        El motor Rust soporta wait_for_data() asíncrono sin polling.
        El motor Python utiliza polling cada ~50ms (menos eficiente pero funcional).

        Returns:
            bool: True si streaming está disponible (siempre True con fallback polling).
        """
        return True  # Todos los modos soportan streaming (Rust: async, Python: polling)

    def is_using_rust_engine(self) -> bool:
        """Indica si está usando el motor Rust (streaming nativo sin polling)."""
        return self._rust_recorder is not None or self._zero_copy_recorder is not None

    def _save_wav(self, audio_data: np.ndarray, save_path: Path):
        """Guarda los datos de audio en un archivo WAV."""
        audio_int16 = (audio_data * 32767).astype(np.int16)
        with wave.open(str(save_path), "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())

    def _get_audio_slice(self, num_samples: int) -> np.ndarray:
        """Extrae un segmento de audio del buffer."""
        if self.channels > 1:
            return self._buffer[:num_samples, :]
        return self._buffer[:num_samples]

    def start(self):
        """Inicia la grabación de audio.

        Raises:
            RecordingError: Si la grabación ya está en progreso o falla al iniciar el stream.
        """
        if self._recording:
            raise RecordingError("grabación ya en progreso")

        self._recording = True

        # --- CAMINO DE EJECUCIÓN ZERO-COPY ---
        if self._zero_copy_recorder:
            try:
                self._zero_copy_recorder.start()
                # Conectar a la memoria compartida para lecturas zero-copy
                self._shm = shared_memory.SharedMemory(name=self._shm_name)
                logger.info(f"grabación iniciada (zero-copy engine, shm={self._shm_name})")
                return
            except Exception as e:
                logger.error(f"fallo en motor zero-copy, intentando standard: {e}")
                self._zero_copy_recorder = None
                self._shm = None

        # --- CAMINO DE EJECUCIÓN RUST STANDARD ---
        if self._rust_recorder:
            try:
                self._rust_recorder.start()
                logger.info("grabación iniciada (rust engine)")
                return
            except Exception as e:
                logger.error(f"fallo en motor rust, intentando fallback a python: {e}")
                # No lanzamos error aquí, permitimos que continúe al fallback Python
                # pero primero debemos resetear el estado de grabación si rust lo dejó sucio
                self._rust_recorder = None  # Deshabilitamos rust para esta instancia

        # --- CAMINO DE EJECUCIÓN PYTHON (FALLBACK) ---
        # Aseguramos que _buffer está inicializado si falló rust
        if self._buffer is None:
            self._buffer = self._allocate_buffer()

        self._write_pos = 0  # reiniciar posición del buffer
        self._last_read_pos = 0  # reiniciar posición de lectura para streaming

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
                        self._buffer[self._write_pos : end_pos, :] = indata[:samples_to_write, :]
                    else:
                        self._buffer[self._write_pos : end_pos] = indata[:samples_to_write, 0]

                    self._write_pos = end_pos

        try:
            if sd is None:
                raise OSError("PortAudio library not found")
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=callback,
                dtype="float32",
                device=self.device_index,
                blocksize=self.CHUNK_SIZE,
            )
            self._stream.start()
            logger.info("grabación de audio iniciada (python fallback)")
        except Exception as e:
            self._recording = False
            if self._stream:
                self._stream.close()
                self._stream = None
            raise RecordingError(f"falló al iniciar la grabación {e}") from e

    def stop(self, save_path: Path | None = None, return_data: bool = True, copy_data: bool = True) -> np.ndarray:
        """Detiene la grabación y devuelve el audio capturado.

        Args:
            save_path: Ruta opcional para guardar el audio como archivo WAV.
            return_data: Si es True retorna el audio grabado.
            copy_data: Si es True retorna una copia del buffer (seguro).

        Returns:
            np.ndarray: El audio grabado como un array de numpy float32.
        """
        if not self._recording:
            raise RecordingError("no hay grabación en curso")

        self._recording = False

        # --- CAMINO DE EJECUCIÓN ZERO-COPY ---
        if self._zero_copy_recorder:
            try:
                # Cerrar conexión a memoria compartida del lado Python
                if self._shm:
                    self._shm.close()
                    self._shm = None

                # El método stop de Rust devuelve el numpy array re-muestreado
                audio_view = self._zero_copy_recorder.stop()
                recorded_samples = len(audio_view)
                logger.info(f"grabación detenida (zero-copy engine): {recorded_samples} samples")

                if save_path:
                    self._save_wav(audio_view, save_path)

                if not return_data:
                    return self._empty_audio_array()

                if copy_data:
                    return audio_view.copy()

                return audio_view
            except Exception as e:
                logger.error(f"error deteniendo grabación zero-copy: {e}")
                raise RecordingError(f"error deteniendo zero-copy: {e}") from e

        # --- CAMINO DE EJECUCIÓN RUST STANDARD ---
        if self._rust_recorder:
            try:
                # El método stop de Rust devuelve directamente el numpy array
                audio_view = self._rust_recorder.stop()
                recorded_samples = len(audio_view)
                logger.info(f"grabación detenida (rust engine): {recorded_samples} samples")

                # Manejo de guardado a disco
                if save_path:
                    self._save_wav(audio_view, save_path)

                if not return_data:
                    return self._empty_audio_array()

                # Rust devuelve un nuevo array (ya es una copia/nueva ref),
                # pero si el usuario pidió copy_data=True explícitamente y queremos ser paranoicos
                if copy_data:
                    return audio_view.copy()

                return audio_view
            except Exception as e:
                logger.error(f"error deteniendo grabación rust: {e}")
                raise RecordingError(f"error deteniendo rust: {e}") from e

        # --- CAMINO DE EJECUCIÓN PYTHON ---
        with self._lock:
            recorded_samples = self._write_pos

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        logger.info(f"grabación detenida (python): {recorded_samples} samples")

        if recorded_samples == 0:
            return self._empty_audio_array()

        audio_view = self._get_audio_slice(recorded_samples)

        if save_path:
            self._save_wav(audio_view, save_path)

        if not return_data:
            return self._empty_audio_array()

        if copy_data:
            return audio_view.copy()

        return audio_view

    # =========================================================================
    # STREAMING METHODS (Rust: async notify, Python: polling fallback)
    # =========================================================================

    async def wait_for_data(self, poll_interval: float = 0.05) -> None:
        """Wait asynchronously for new audio data to be available.

        For Rust engine: Uses tokio::Notify for efficient async waiting.
        For Python fallback: Polls buffer write position every poll_interval.

        Args:
            poll_interval: Seconds between polls for Python fallback (default 50ms).

        Raises:
            RuntimeError: If not recording.
        """
        if not self._recording:
            raise RuntimeError("not recording")

        if self._zero_copy_recorder:
            await self._zero_copy_recorder.wait_for_data()
            return

        if self._rust_recorder:
            await self._rust_recorder.wait_for_data()
            return

        # --- PYTHON FALLBACK: polling-based streaming ---
        # Esperamos hasta que haya nuevos datos en el buffer
        while self._recording:
            with self._lock:
                if self._write_pos > self._last_read_pos:
                    return  # Hay datos nuevos disponibles
            await asyncio.sleep(poll_interval)

    def read_chunk(self) -> "np.ndarray":
        """Read available audio data from the ring buffer.

        Returns all samples currently in the buffer without blocking.
        Used for streaming transcription where we process audio incrementally.

        Returns:
            np.ndarray: Audio samples as float32 numpy array.
        """
        if not self._recording:
            return np.array([], dtype=np.float32)

        if self._zero_copy_recorder:
            return self._zero_copy_recorder.read_chunk()

        if self._rust_recorder:
            return self._rust_recorder.read_chunk()

        # --- PYTHON FALLBACK: lectura incremental del buffer ---
        with self._lock:
            if self._write_pos <= self._last_read_pos:
                return np.array([], dtype=np.float32)

            # Extraer solo los samples nuevos desde la última lectura
            start = self._last_read_pos
            end = self._write_pos
            self._last_read_pos = end

            if self.channels > 1:
                return self._buffer[start:end, :].copy()
            return self._buffer[start:end].copy()

    # =========================================================================
    # ZERO-COPY METHODS (SOTA 2026 - direct /dev/shm access)
    # =========================================================================

    def read_chunk_zero_copy(self) -> "np.ndarray":
        """Read available audio data directly from shared memory (zero-copy).

        This method provides true zero-copy access to audio data by returning
        a NumPy array backed by the shared memory segment. The array is a view
        into the Rust-managed buffer, not a copy.

        WARNING: The returned array is only valid while recording. Do not store
        references to it after calling stop().

        Returns:
            np.ndarray: Audio samples as float32 numpy array (view, not copy).

        Raises:
            RuntimeError: If not using zero-copy recorder or not recording.
        """
        if not self._zero_copy_recorder:
            raise RuntimeError("read_chunk_zero_copy requires ZeroCopyAudioRecorder")
        if not self._shm:
            raise RuntimeError("shared memory not connected")
        if not self._recording:
            return np.array([], dtype=np.float32)

        # Obtener número de samples disponibles
        num_samples = self._zero_copy_recorder.get_available_samples()
        if num_samples == 0:
            return np.array([], dtype=np.float32)

        # Vista zero-copy directa a la memoria compartida
        # Cada sample float32 ocupa 4 bytes
        byte_len = num_samples * 4
        return np.frombuffer(self._shm.buf[:byte_len], dtype=np.float32)

    def get_shm_name(self) -> str | None:
        """Get the shared memory segment name for external access.

        Returns:
            str | None: The /dev/shm segment name, or None if not using zero-copy.
        """
        return self._shm_name

    def is_zero_copy_enabled(self) -> bool:
        """Check if zero-copy mode is active.

        Returns:
            bool: True if using ZeroCopyAudioRecorder with SharedMemory.
        """
        return self._zero_copy_recorder is not None and self._shm is not None
