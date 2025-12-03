"""Pruebas unitarias para regresiones y bugs corregidos en AudioRecorder.

Este archivo contiene pruebas diseñadas para reproducir y evitar la reaparición
de bugs específicos encontrados en `AudioRecorder`.

Pruebas incluidas:
    - Resource leak en `start()`: Verifica que el stream se cierre si falla `start()`.

Ejecución:
    >>> pytest tests/unit/test_audio_recorder_regressions.py
"""

import unittest
from unittest.mock import MagicMock, patch
from v2m.infrastructure.audio.recorder import AudioRecorder
from v2m.domain.errors import RecordingError

class TestAudioRecorderRegressions(unittest.TestCase):
    def setUp(self):
        self.recorder = AudioRecorder()

    @patch('v2m.infrastructure.audio.recorder.sd')
    def test_start_failure_cleans_up_resources(self, mock_sd):
        """
        Verifica que si stream.start() falla, se limpien los recursos correctamente.

        Bug corregido:
            Anteriormente, si `self._stream.start()` lanzaba una excepción,
            `self._stream` quedaba asignado pero en un estado inconsistente,
            y `_recording` quedaba en False. Esto podía causar fugas de recursos
            o errores en intentos posteriores de `start()`.

        Comportamiento esperado:
            - Se debe lanzar RecordingError.
            - `self._recording` debe ser False.
            - `self._stream` debe ser None (limpiado).
            - Se debe haber llamado a `stream.close()`.
        """
        # Arrange
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        # Simular fallo en start()
        mock_stream.start.side_effect = Exception("Simulated start failure")

        # Act & Assert
        with self.assertRaises(RecordingError):
            self.recorder.start()

        self.assertFalse(self.recorder._recording)
        self.assertIsNone(self.recorder._stream, "El stream debería ser None tras un fallo en start()")
        mock_stream.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()
