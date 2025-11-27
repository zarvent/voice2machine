
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from v2m.infrastructure.audio.recorder import AudioRecorder
from v2m.domain.errors import RecordingError

class TestAudioRecorder(unittest.TestCase):
    def setUp(self):
        self.recorder = AudioRecorder()

    @patch('v2m.infrastructure.audio.recorder.sd')
    def test_stop_clears_frames(self, mock_sd):
        """Test that stop() clears internal frames so subsequent calls raise RecordingError."""
        # Setup mock stream
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        # Start recording
        self.recorder.start()

        # Simulate some data
        fake_data = np.zeros((16000, 1), dtype=np.float32)
        self.recorder._frames.append(fake_data)

        # First stop - should return audio
        audio1 = self.recorder.stop()
        self.assertEqual(len(audio1), 16000)

        # Second stop - should raise RecordingError
        with self.assertRaises(RecordingError):
            self.recorder.stop()

if __name__ == '__main__':
    unittest.main()
