class ApplicationError(Exception):
    """Base class for application errors."""
    pass

class MicrophoneNotFoundError(ApplicationError):
    """Raised when no microphone is detected."""
    pass

class RecordingError(ApplicationError):
    """Raised when there is an error during recording."""
    pass

class TranscriptionError(ApplicationError):
    """Raised when there is an error during transcription."""
    pass

class LLMError(ApplicationError):
    """Raised when there is an error with the language model."""
    pass
