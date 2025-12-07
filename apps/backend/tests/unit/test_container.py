"""Pruebas unitarias para el contenedor de inyección de dependencias.

Este módulo verifica que el contenedor configure correctamente las dependencias,
respetando las opciones definidas en el archivo de configuración.
"""

import unittest
from unittest.mock import patch, MagicMock
from v2m.config import Settings, VadParametersConfig, WhisperConfig
from v2m.infrastructure.vad_service import VADService

class TestContainerConfiguration(unittest.TestCase):
    """Verifica la correcta inicialización de servicios en el contenedor."""

    @patch('v2m.core.di.container.VADService')
    @patch('v2m.core.di.container.WhisperTranscriptionService')
    @patch('v2m.core.di.container.GeminiLLMService')
    @patch('v2m.core.di.container.LinuxNotificationService')
    @patch('v2m.core.di.container.LinuxClipboardAdapter')
    @patch('v2m.core.di.container.CommandBus')
    @patch('v2m.core.di.container.StartRecordingHandler')
    @patch('v2m.core.di.container.StopRecordingHandler')
    @patch('v2m.core.di.container.ProcessTextHandler')
    @patch('v2m.core.di.container.ThreadPoolExecutor')
    def test_container_injects_vad_backend_preference(
        self,
        MockExecutor, MockProcessHandler, MockStopHandler, MockStartHandler,
        MockCommandBus, MockClipboard, MockNotification, MockLLM, MockWhisper, MockVAD
    ):
        """
        Verifica que si la configuración especifica backend='torch',
        el VADService se inicialice con prefer_onnx=False.
        """
        # Arrange: Configurar mock de settings con backend='torch'
        mock_settings = MagicMock()
        mock_settings.whisper.vad_parameters.backend = 'torch'

        # Patch `v2m.core.di.container.config` antes de importar Container
        # para asegurar que use nuestra configuración simulada.
        # Nota: Como v2m.core.di.container ya podría estar importado en memoria,
        # re-importamos dentro del patch para forzar el uso del mock.
        import v2m.core.di.container

        with patch('v2m.core.di.container.config', mock_settings):
             from v2m.core.di.container import Container

             # Act: Instanciar el contenedor
             _ = Container()

             # Assert: VADService debe haber recibido prefer_onnx=False
             MockVAD.assert_called_with(prefer_onnx=False)

    @patch('v2m.core.di.container.VADService')
    @patch('v2m.core.di.container.WhisperTranscriptionService')
    @patch('v2m.core.di.container.GeminiLLMService')
    @patch('v2m.core.di.container.LinuxNotificationService')
    @patch('v2m.core.di.container.LinuxClipboardAdapter')
    @patch('v2m.core.di.container.CommandBus')
    @patch('v2m.core.di.container.StartRecordingHandler')
    @patch('v2m.core.di.container.StopRecordingHandler')
    @patch('v2m.core.di.container.ProcessTextHandler')
    @patch('v2m.core.di.container.ThreadPoolExecutor')
    def test_container_injects_vad_backend_onnx_preference(
        self,
        MockExecutor, MockProcessHandler, MockStopHandler, MockStartHandler,
        MockCommandBus, MockClipboard, MockNotification, MockLLM, MockWhisper, MockVAD
    ):
        """
        Verifica que si la configuración especifica backend='onnx',
        el VADService se inicialice con prefer_onnx=True.
        """
        mock_settings = MagicMock()
        mock_settings.whisper.vad_parameters.backend = 'onnx'

        with patch('v2m.core.di.container.config', mock_settings):
             from v2m.core.di.container import Container
             _ = Container()
             MockVAD.assert_called_with(prefer_onnx=True)

if __name__ == '__main__':
    unittest.main()
