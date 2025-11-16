import argparse
import sys
import subprocess
from whisper_dictation.core.di.container import container
from whisper_dictation.application.commands import StartRecordingCommand, StopRecordingCommand, ProcessTextCommand
from whisper_dictation.domain.errors import ApplicationError
from whisper_dictation.core.logging import logger

def send_notification(title: str, message: str) -> None:
    subprocess.run(["notify-send", title, message])

def main() -> None:
    parser = argparse.ArgumentParser(description="Whisper Dictation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("start", help="Start recording audio.")
    subparsers.add_parser("stop", help="Stop recording and transcribe.")
    subparsers.add_parser("process", help="Process text with Gemini.")

    args, unknown = parser.parse_known_args()

    command_bus = container.get_command_bus()

    try:
        if args.command == "start":
            command_bus.dispatch(StartRecordingCommand())
        elif args.command == "stop":
            command_bus.dispatch(StopRecordingCommand())
        elif args.command == "process":
            text_to_process = ""
            if not sys.stdin.isatty():
                text_to_process = sys.stdin.read().strip()
            elif unknown:
                text_to_process = " ".join(unknown)

            if text_to_process:
                command_bus.dispatch(ProcessTextCommand(text_to_process))
            else:
                raise ValueError("No text provided to process.")

    except ApplicationError as e:
        logger.error(str(e))
        send_notification("❌ Error", str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred.")
        send_notification("❌ Error Inesperado", "Ocurrió un error inesperado.")
        sys.exit(1)

if __name__ == "__main__":
    main()
