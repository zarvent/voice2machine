"""Pruebas unitarias para el servicio de Detección de Actividad de Voz (VAD).

Este módulo contiene las pruebas unitarias para verificar el correcto
funcionamiento del servicio VADService, que es responsable de detectar
y extraer segmentos de audio que contienen voz humana.

El servicio VAD es crítico para optimizar el procesamiento de audio,
eliminando silencios y ruido de fondo antes de enviar el audio al
modelo de transcripción.

Las pruebas incluyen:
    - Procesamiento de audio vacío.
    - Procesamiento de audio sin voz detectada.
    - Procesamiento de audio con segmentos de voz.
    - Verificación de uso correcto del umbral configurado.

Ejemplo de uso típico:
    pytest tests/unit/test_vad_service.py -v
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from v2m.infrastructure.vad_service import VADService


@pytest.fixture
def vad_service() -> VADService:
    return VADService()

@pytest.fixture
def configured_vad_service():
    """VADService with mocked model and utils so process() works without real model."""
    service = VADService()
    service.load_model = MagicMock()
    service.model = MagicMock()  # Needs to be non-None for process() to proceed
    return service

def test_vad_process_empty_audio(vad_service):
    """Test processing empty audio returns empty array."""
    # Mock load_model to avoid downloading/loading real model
    vad_service.load_model = MagicMock()
    vad_service.get_speech_timestamps = MagicMock(return_value=[])

    empty_audio = np.array([], dtype=np.float32)
    result = vad_service.process(empty_audio)

    assert result.size == 0

def test_vad_process_no_speech(configured_vad_service):
    """Test processing audio with no speech returns empty array."""
    configured_vad_service.get_speech_timestamps = MagicMock(return_value=[])

    # 1 second of silence
    audio = np.zeros(16000, dtype=np.float32)
    result = configured_vad_service.process(audio)

    assert result.size == 0

def test_vad_process_with_speech(configured_vad_service):
    """Test processing audio with speech returns concatenated segments."""
    # Mock timestamps: speech from 1000-2000 and 3000-4000
    configured_vad_service.get_speech_timestamps = MagicMock(return_value=[
        {'start': 1000, 'end': 2000},
        {'start': 3000, 'end': 4000}
    ])

    # Create dummy audio
    audio = np.arange(5000, dtype=np.float32)

    result = configured_vad_service.process(audio)

    # Expected size: (2000-1000) + (4000-3000) = 1000 + 1000 = 2000
    assert result.size == 2000
    # Verify content
    expected = np.concatenate([audio[1000:2000], audio[3000:4000]])
    np.testing.assert_array_equal(result, expected)

def test_vad_uses_configured_threshold(configured_vad_service):
    """Test that VADService uses the threshold from config instead of hardcoded value.

    This test verifies that the bug fix is in place - the VAD threshold should come
    from config.whisper.vad_parameters.threshold, not be hardcoded to 0.5.
    """
    configured_vad_service.get_speech_timestamps = MagicMock(return_value=[
        {'start': 0, 'end': 1000}
    ])

    audio = np.arange(1000, dtype=np.float32)

    with patch('v2m.infrastructure.vad_service.config') as mock_config:
        # Set a custom threshold that's different from the default 0.5
        mock_config.whisper.vad_parameters.threshold = 0.7

        configured_vad_service.process(audio)

        # Verify get_speech_timestamps was called with the configured threshold
        call_args = configured_vad_service.get_speech_timestamps.call_args
        assert call_args.kwargs['threshold'] == 0.7, \
            "VADService should use the configured threshold, not a hardcoded value"
