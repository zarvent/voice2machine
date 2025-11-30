"""Pruebas unitarias del grabador de audio (AudioRecorder).

Propósito
---------
Validar el comportamiento del componente AudioRecorder, responsable de la
captura de audio desde dispositivos de entrada del sistema operativo.

Contexto técnico
----------------
El AudioRecorder implementa el patrón de acumulación de frames: durante la
grabación, almacena fragmentos de audio (frames) en un buffer interno. Al
detenerse, concatena estos frames y limpia el estado interno.

Este archivo verifica específicamente:
    * Que stop() retorne el audio acumulado correctamente.
    * Que stop() reinicie el estado interno (principio de idempotencia).
    * Que llamadas subsecuentes a stop() fallen de forma controlada.

Estrategia de testing
---------------------
Usamos test doubles (específicamente mocks) para aislar el componente del
hardware de audio real. Esto nos da:
    * Velocidad: No dependemos de dispositivos físicos.
    * Determinismo: El mismo test produce el mismo resultado siempre.
    * Portabilidad: Funciona en CI/CD sin configuración de audio.

Referencias
-----------
    * Mock Objects: Fowler, M. (2007). "Mocks Aren't Stubs"
    * Patrón AAA: Beck, K. "Test-Driven Development by Example"

Ejecución
---------
    >>> pytest tests/unit/test_audio_recorder.py -v
"""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from v2m.infrastructure.audio.recorder import AudioRecorder
from v2m.domain.errors import RecordingError


class TestAudioRecorder(unittest.TestCase):
    """Suite de pruebas para AudioRecorder.

    Esta clase agrupa las pruebas relacionadas con el ciclo de vida del
    grabador: inicio, captura y detención de grabaciones de audio.

    ¿Por qué unittest.TestCase?
        Aunque pytest es más moderno, unittest viene incluido en Python
        y ofrece setUp()/tearDown() para preparar el entorno de cada test.
        Ambos frameworks son válidos; aquí usamos unittest por consistencia.

    Attributes:
        recorder (AudioRecorder): Sistema bajo prueba (SUT). Se reinstancia
            antes de cada test para garantizar aislamiento.

    Note:
        El aislamiento entre tests es fundamental. Si un test modifica el
        estado del recorder, no debe afectar a los demás. Por eso usamos
        setUp() para crear una instancia fresca cada vez.
    """

    def setUp(self) -> None:
        """Inicializa el entorno de prueba (fase Arrange del patrón AAA).

        Este método se ejecuta automáticamente antes de cada test method.
        Garantiza que cada prueba comience con un AudioRecorder en estado
        inicial, sin contaminación de tests anteriores.

        Patrón de diseño:
            Corresponde al concepto de "Test Fixture" - el estado conocido
            desde el cual se ejecuta cada prueba.
        """
        self.recorder = AudioRecorder()

    @patch('v2m.infrastructure.audio.recorder.sd')
    def test_stop_clears_frames(self, mock_sd: MagicMock) -> None:
        """Verifica que stop() libere el buffer interno después de retornar.

        Caso de prueba
        --------------
        Validar que el AudioRecorder siga el principio de "single use":
        cada llamada a stop() entrega el audio acumulado y reinicia el
        estado. Llamadas adicionales sin nueva grabación deben fallar.

        Motivación
        ----------
        Sin este comportamiento, tendríamos varios problemas:
            1. Memory leaks: Los frames se acumularían indefinidamente.
            2. Datos duplicados: Podrías obtener el mismo audio varias veces.
            3. Mezcla de grabaciones: Audio de sesiones anteriores contaminaría
               las nuevas.

        Metodología (patrón AAA)
        ------------------------
        Arrange:
            - Crear mock del módulo sounddevice
            - Iniciar grabación simulada
            - Inyectar 1 segundo de audio falso (16000 muestras a 16kHz)

        Act:
            - Primera llamada a stop(): debe retornar el audio

        Assert:
            - El audio retornado tiene la longitud correcta (16000 muestras)
            - Segunda llamada a stop(): debe lanzar RecordingError

        Args:
            mock_sd: Test double que reemplaza al módulo sounddevice.
                Nos permite simular la captura de audio sin hardware real.

        Raises:
            AssertionError: Si el audio no tiene 16000 muestras.
            AssertionError: Si la segunda llamada a stop() no lanza excepción.
        """
        # ARRANGE: Configuramos el entorno de prueba
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        self.recorder.start()

        # Inyectamos datos de prueba: 1 segundo de silencio
        # 16000 muestras porque trabajamos a 16kHz (estándar en procesamiento de voz)
        fake_data = np.zeros((16000, 1), dtype=np.float32)
        self.recorder._frames.append(fake_data)

        # ACT: Ejecutamos la acción que queremos probar
        audio1 = self.recorder.stop()

        # ASSERT: Verificamos el comportamiento esperado
        self.assertEqual(len(audio1), 16000)

        # La segunda llamada debe fallar - no hay nada que devolver
        with self.assertRaises(RecordingError):
            self.recorder.stop()


if __name__ == '__main__':
    unittest.main()
