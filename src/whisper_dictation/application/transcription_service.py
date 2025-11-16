from abc import ABC, abstractmethod

class TranscriptionService(ABC):
    """Abstract base class for transcription services."""

    @abstractmethod
    def start_recording(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop_and_transcribe(self) -> str:
        raise NotImplementedError
