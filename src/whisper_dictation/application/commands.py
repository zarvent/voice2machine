from whisper_dictation.core.cqrs.command import Command

class StartRecordingCommand(Command):
    """Command to start recording audio."""
    pass

class StopRecordingCommand(Command):
    """Command to stop recording and transcribe audio."""
    pass

class ProcessTextCommand(Command):
    """Command to process text with a language model."""
    def __init__(self, text: str) -> None:
        self.text = text
