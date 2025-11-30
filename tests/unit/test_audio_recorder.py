"""Pruebas unitarias para el módulo AudioRecorder.

Este módulo contiene las pruebas unitarias para verificar el correcto
funcionamiento del componente AudioRecorder, que es responsable de la
captura de audio desde el micrófono del sistema.

Las pruebas incluyen:
    - Verificación de que el método stop() limpia los frames internos.
    - Manejo correcto de errores cuando se intenta detener sin grabación activa.

Ejemplo de uso típico:
    pytest tests/unit/test_audio_recorder.py -v
"""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from v2m.infrastructure.audio.recorder import AudioRecorder
from v2m.domain.errors import RecordingError


class TestAudioRecorder(unittest.TestCase):
    """Suite de pruebas para la clase AudioRecorder.

    Esta clase contiene todas las pruebas unitarias relacionadas con el
    grabador de audio, verificando su comportamiento en diferentes escenarios
    de uso y condiciones de error.

    Attributes:
        recorder: Instancia de AudioRecorder utilizada en cada prueba.
    """

    def setUp(self) -> None:
        """Configura el entorno de prueba antes de cada test.

        Crea una nueva instancia de AudioRecorder para garantizar
        que cada prueba comience con un estado limpio y aislado.
        """
        self.recorder = AudioRecorder()

    @patch('v2m.infrastructure.audio.recorder.sd')
    def test_stop_clears_frames(self, mock_sd: MagicMock) -> None:
        """Verifica que stop() limpia los frames internos correctamente.

        Esta prueba asegura que después de llamar a stop() por primera vez,
        los frames internos se limpian completamente, y cualquier llamada
        subsecuente a stop() lanzará un RecordingError.

        Args:
            mock_sd: Mock del módulo sounddevice para simular el stream de audio.

        Raises:
            AssertionError: Si el audio retornado no tiene la longitud esperada.
            AssertionError: Si la segunda llamada a stop() no lanza RecordingError.
        """
        # Configura el mock del stream
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        # Inicia la grabación
        self.recorder.start()

        # Simula algunos datos de audio
        fake_data = np.zeros((16000, 1), dtype=np.float32)
        self.recorder._frames.append(fake_data)

        # Primera llamada a stop - debe retornar el audio grabado
        audio1 = self.recorder.stop()
        self.assertEqual(len(audio1), 16000)

        # Segunda llamada a stop - debe lanzar RecordingError
        with self.assertRaises(RecordingError):
            self.recorder.stop()


if __name__ == '__main__':
    unittest.main()
