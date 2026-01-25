"""Pruebas para el puente zero-copy vía SharedMemory (SOTA 2026).

Este módulo valida la implementación zero-copy que utiliza POSIX Shared Memory
(/dev/shm) para transferir datos de audio entre el motor Rust y Python sin copias.

Arquitectura bajo prueba:
    Rust (v2m_engine) -> SharedMemory -> np.frombuffer -> Python

Propósito
---------
Verificar que:
    * SharedAudioBuffer asigna y libera memoria compartida correctamente.
    * ZeroCopyAudioRecorder integra captura + SharedMemory.
    * El acceso vía np.frombuffer no incurre en copias intermedias.
    * Los contadores atómicos (write_pos) son consistentes.
    * El canal flume envía notificaciones lock-free.

Requisitos
----------
    * Motor Rust compilado (v2m_engine)
    * Linux con /dev/shm disponible

Ejecución
---------
    >>> pytest tests/unit/test_zero_copy_shm_bridge.py -v

    # Solo si el motor Rust está disponible
    >>> pytest tests/unit/test_zero_copy_shm_bridge.py -v -m "not rust_required"
"""

import unittest
from multiprocessing import shared_memory
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Intentamos importar el motor Rust
try:
    from v2m_engine import SharedAudioBuffer, ZeroCopyAudioRecorder

    HAS_RUST_ENGINE = True
except ImportError:
    HAS_RUST_ENGINE = False
    SharedAudioBuffer = None
    ZeroCopyAudioRecorder = None


# Marker para tests que requieren motor Rust
rust_required = pytest.mark.skipif(
    not HAS_RUST_ENGINE, reason="Requiere v2m_engine compilado"
)


@rust_required
class TestSharedAudioBuffer(unittest.TestCase):
    """Pruebas para SharedAudioBuffer (Rust-managed SharedMemory)."""

    def test_shared_buffer_creation(self) -> None:
        """Verifica que SharedAudioBuffer crea segmento en /dev/shm."""
        # ARRANGE & ACT
        buffer = SharedAudioBuffer(capacity_samples=16000)

        # ASSERT
        shm_name = buffer.get_shm_name()
        self.assertIsNotNone(shm_name)
        self.assertTrue(shm_name.startswith("v2m_audio_"))

        # Verificar que podemos conectar desde Python
        shm = shared_memory.SharedMemory(name=shm_name)
        self.assertIsNotNone(shm.buf)
        shm.close()

    def test_shared_buffer_capacity(self) -> None:
        """Verifica que la capacidad se respeta correctamente."""
        # ARRANGE & ACT
        capacity = 32000
        buffer = SharedAudioBuffer(capacity_samples=capacity)

        # ASSERT
        self.assertEqual(buffer.get_capacity(), capacity)
        self.assertEqual(buffer.get_data_len(), 0)  # Vacío inicialmente

    def test_shared_buffer_read_as_numpy(self) -> None:
        """Verifica que read_as_numpy devuelve datos correctos."""
        # ARRANGE
        buffer = SharedAudioBuffer(capacity_samples=16000)

        # ACT: El buffer está vacío, debe retornar array vacío
        data = buffer.read_as_numpy()

        # ASSERT
        self.assertEqual(len(data), 0)
        self.assertEqual(data.dtype, np.float32)


@rust_required
class TestZeroCopyAudioRecorder(unittest.TestCase):
    """Pruebas para ZeroCopyAudioRecorder (integración completa)."""

    def test_recorder_creation_with_shm(self) -> None:
        """Verifica que ZeroCopyAudioRecorder crea SharedMemory correctamente."""
        # ARRANGE & ACT
        recorder = ZeroCopyAudioRecorder(
            sample_rate=16000, channels=1, max_duration_sec=10
        )

        # ASSERT
        shm_name = recorder.get_shm_name()
        self.assertIsNotNone(shm_name)
        self.assertTrue(shm_name.startswith("v2m_audio_"))
        self.assertFalse(recorder.is_recording())

    def test_recorder_initial_state(self) -> None:
        """Verifica estado inicial del recorder."""
        # ARRANGE & ACT
        recorder = ZeroCopyAudioRecorder()

        # ASSERT
        self.assertFalse(recorder.is_recording())
        self.assertEqual(recorder.get_available_samples(), 0)


class TestAudioRecorderFacadeZeroCopy(unittest.TestCase):
    """Pruebas para el facade AudioRecorder en modo zero_copy."""

    def setUp(self) -> None:
        """Configura el entorno de prueba."""
        # Importamos aquí para evitar errores de importación circular
        from v2m.features.audio.recorder import AudioRecorder, HAS_ZERO_COPY

        self.AudioRecorder = AudioRecorder
        self.has_zero_copy = HAS_ZERO_COPY

    @pytest.mark.skipif(not HAS_RUST_ENGINE, reason="Requiere v2m_engine")
    def test_facade_zero_copy_mode_enabled(self) -> None:
        """Verifica que el facade detecta y usa modo zero-copy."""
        # ARRANGE & ACT
        recorder = self.AudioRecorder(mode="zero_copy")

        # ASSERT
        if self.has_zero_copy:
            self.assertTrue(recorder._zero_copy_recorder is not None)
            self.assertIsNotNone(recorder._shm_name)
        else:
            # Fallback si Rust no está disponible
            self.assertIsNone(recorder._zero_copy_recorder)

    def test_facade_fallback_mode(self) -> None:
        """Verifica que mode='fallback' fuerza el motor Python."""
        # ARRANGE & ACT
        with patch("v2m.features.audio.recorder.HAS_RUST_ENGINE", False):
            with patch("v2m.features.audio.recorder.HAS_ZERO_COPY", False):
                from v2m.features.audio.recorder import AudioRecorder

                recorder = AudioRecorder(mode="fallback")

                # ASSERT: Debe usar fallback Python
                self.assertIsNone(recorder._zero_copy_recorder)
                self.assertIsNone(recorder._rust_recorder)

    def test_is_zero_copy_enabled_method(self) -> None:
        """Verifica método is_zero_copy_enabled()."""
        # ARRANGE
        with patch("v2m.features.audio.recorder.HAS_RUST_ENGINE", False):
            with patch("v2m.features.audio.recorder.HAS_ZERO_COPY", False):
                from v2m.features.audio.recorder import AudioRecorder

                recorder = AudioRecorder(mode="fallback")

                # ACT & ASSERT
                self.assertFalse(recorder.is_zero_copy_enabled())

    def test_get_shm_name_without_zero_copy(self) -> None:
        """Verifica que get_shm_name retorna None sin zero-copy."""
        # ARRANGE
        with patch("v2m.features.audio.recorder.HAS_RUST_ENGINE", False):
            with patch("v2m.features.audio.recorder.HAS_ZERO_COPY", False):
                from v2m.features.audio.recorder import AudioRecorder

                recorder = AudioRecorder(mode="fallback")

                # ACT & ASSERT
                self.assertIsNone(recorder.get_shm_name())


@rust_required
class TestZeroCopyDataIntegrity(unittest.TestCase):
    """Pruebas de integridad de datos en modo zero-copy.

    Estas pruebas verifican que los datos transferidos vía SharedMemory
    mantienen su integridad y que np.frombuffer funciona correctamente.
    """

    def test_shared_memory_python_access(self) -> None:
        """Verifica que Python puede leer SharedMemory creada por Rust."""
        # ARRANGE
        buffer = SharedAudioBuffer(capacity_samples=1000)
        shm_name = buffer.get_shm_name()

        # ACT: Conectar desde Python
        shm = shared_memory.SharedMemory(name=shm_name)

        # ASSERT: La memoria es accesible
        self.assertIsNotNone(shm.buf)
        self.assertGreater(len(shm.buf), 0)

        # Verificar tamaño (1000 samples * 4 bytes/float32)
        expected_size = 1000 * 4
        self.assertGreaterEqual(shm.size, expected_size)

        shm.close()

    def test_np_frombuffer_creates_view(self) -> None:
        """Verifica que np.frombuffer crea una vista, no una copia."""
        # ARRANGE
        buffer = SharedAudioBuffer(capacity_samples=1000)
        shm_name = buffer.get_shm_name()
        shm = shared_memory.SharedMemory(name=shm_name)

        try:
            # ACT: Crear array NumPy desde buffer
            audio = np.frombuffer(shm.buf[:100 * 4], dtype=np.float32)

            # ASSERT: Verificar que es una vista (no copia)
            # Una vista no es propietaria de sus datos
            self.assertFalse(audio.flags.owndata)
            self.assertEqual(audio.dtype, np.float32)
            self.assertEqual(len(audio), 100)

            # IMPORTANTE: En Python 3.12+, debemos asegurarnos de que no hay
            # punteros exportados antes de cerrar la memoria compartida.
            del audio
        finally:
            shm.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
