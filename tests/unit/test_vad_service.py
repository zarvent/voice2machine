import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from whisper_dictation.infrastructure.vad_service import VADService

@pytest.fixture
def vad_service():
    return VADService()

def test_vad_process_empty_audio(vad_service):
    """Test processing empty audio returns empty array."""
    # Mock load_model to avoid downloading/loading real model
    vad_service.load_model = MagicMock()
    vad_service.get_speech_timestamps = MagicMock(return_value=[])

    empty_audio = np.array([], dtype=np.float32)
    result = vad_service.process(empty_audio)

    assert result.size == 0

def test_vad_process_no_speech(vad_service):
    """Test processing audio with no speech returns empty array."""
    vad_service.load_model = MagicMock()
    vad_service.get_speech_timestamps = MagicMock(return_value=[])

    # 1 second of silence
    audio = np.zeros(16000, dtype=np.float32)
    result = vad_service.process(audio)

    assert result.size == 0

def test_vad_process_with_speech(vad_service):
    """Test processing audio with speech returns concatenated segments."""
    vad_service.load_model = MagicMock()
    # Mock timestamps: speech from 1000-2000 and 3000-4000
    vad_service.get_speech_timestamps = MagicMock(return_value=[
        {'start': 1000, 'end': 2000},
        {'start': 3000, 'end': 4000}
    ])

    # Create dummy audio
    audio = np.arange(5000, dtype=np.float32)

    result = vad_service.process(audio)

    # Expected size: (2000-1000) + (4000-3000) = 1000 + 1000 = 2000
    assert result.size == 2000
    # Verify content
    expected = np.concatenate([audio[1000:2000], audio[3000:4000]])
    np.testing.assert_array_equal(result, expected)
