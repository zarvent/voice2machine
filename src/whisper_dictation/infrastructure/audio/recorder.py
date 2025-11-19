import sounddevice as sd
import numpy as np
import threading
import wave
from pathlib import Path
from typing import Optional, List
from whisper_dictation.core.logging import logger
from whisper_dictation.domain.errors import RecordingError

class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._recording = False
        self._frames: List[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        # Max duration to prevent OOM: 10 minutes
        self.max_samples = 10 * 60 * sample_rate
        self.current_samples = 0

    def start(self):
        if self._recording:
            raise RecordingError("Recording already in progress")

        self._recording = True
        self._frames = []
        self.current_samples = 0

        def callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio recording status: {status}")
            with self._lock:
                if self._recording:
                    if self.current_samples < self.max_samples:
                        self._frames.append(indata.copy())
                        self.current_samples += frames
                    else:
                        # Stop recording if max duration reached (or just stop appending)
                        pass

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=callback,
                dtype="float32"
            )
            self._stream.start()
            logger.info("Audio recording started")
        except Exception as e:
            self._recording = False
            raise RecordingError(f"Failed to start recording: {e}") from e

    def stop(self, save_path: Optional[Path] = None) -> np.ndarray:
        if not self._recording:
             # If frames are empty and not recording, then truly nothing happened
             if not self._frames and not self._stream:
                 raise RecordingError("No recording in progress")

        with self._lock:
            self._recording = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        logger.info("Audio recording stopped")

        if not self._frames:
            return np.array([], dtype=np.float32)

        audio = np.concatenate(self._frames, axis=0).flatten()

        if save_path:
            # Convert float32 to int16 for WAV
            audio_int16 = (audio * 32767).astype(np.int16)
            with wave.open(str(save_path), 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2) # 16 bit
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_int16.tobytes())

        return audio
