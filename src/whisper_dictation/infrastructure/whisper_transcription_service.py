import time
import subprocess
from pathlib import Path
from typing import Optional
from faster_whisper import WhisperModel
from whisper_dictation.application.transcription_service import TranscriptionService
from whisper_dictation.config import config
from whisper_dictation.domain.errors import MicrophoneNotFoundError, RecordingError
from whisper_dictation.core.logging import logger

class WhisperTranscriptionService(TranscriptionService):
    def __init__(self) -> None:
        self._model: Optional[WhisperModel] = None
        self._paths = config['paths']
        self._recording_flag = Path(self._paths['recording_flag'])
        self._audio_file = Path(self._paths['audio_file'])

    @property
    def model(self) -> WhisperModel:
        if self._model is None:
            logger.info("Loading Whisper model...")
            whisper_config = config['whisper']
            self._model = WhisperModel(
                whisper_config['model'],
                device=whisper_config['device'],
                compute_type=whisper_config['compute_type'],
                device_index=whisper_config['device_index'],
                num_workers=whisper_config['num_workers']
            )
            logger.info("Whisper model loaded.")
        return self._model

    def start_recording(self) -> None:
        if self._recording_flag.exists():
            raise RecordingError("A recording is already in process.")

        if self._audio_file.exists():
            self._audio_file.unlink()

        source = subprocess.getoutput("pactl get-default-source")
        if not source:
            source = subprocess.getoutput("pactl list sources short | grep -v monitor | head -1 | awk '{print $2}'")

        if not source:
            raise MicrophoneNotFoundError("No microphone detected.")

        subprocess.run(["pactl", "set-source-mute", source, "0"])
        subprocess.run(["pactl", "set-source-volume", source, "100%"])

        process = subprocess.Popen([
            "parecord",
            "--device=" + source,
            "--format=s16le",
            "--rate=16000",
            "--channels=1",
            str(self._audio_file)
        ], stderr=subprocess.DEVNULL)

        with open(self._recording_flag, 'w') as f:
            f.write(str(process.pid))
        logger.info("Recording started.")

    def stop_and_transcribe(self) -> str:
        if not self._recording_flag.exists():
            raise RecordingError("No active recording.")

        with open(self._recording_flag, 'r') as f:
            pid = int(f.read())

        try:
            subprocess.run(["kill", "-SIGINT", str(pid)])
            time.sleep(1)
            subprocess.run(["kill", "-9", str(pid)])
        except ProcessLookupError:
            pass

        self._recording_flag.unlink()
        time.sleep(0.5)

        if not self._audio_file.exists() or self._audio_file.stat().st_size < 1000:
            raise RecordingError("No audio was recorded.")

        logger.info("Transcribing audio...")
        whisper_config = config['whisper']
        segments, _ = self.model.transcribe(
            str(self._audio_file),
            language=whisper_config['language'],
            beam_size=whisper_config['beam_size'],
            best_of=whisper_config['best_of'],
            temperature=whisper_config['temperature'],
            vad_filter=whisper_config['vad_filter'],
            vad_parameters=config['whisper']['vad_parameters']
        )
        text = " ".join([segment.text.strip() for segment in segments])
        logger.info("Transcription complete.")

        self._audio_file.unlink()
        return text
