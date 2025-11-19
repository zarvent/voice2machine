import subprocess
import pyperclip
from whisper_dictation.core.interfaces import ClipboardInterface, NotificationInterface
from whisper_dictation.core.logging import logger

class LinuxClipboardAdapter(ClipboardInterface):
    def copy(self, text: str) -> None:
        try:
            pyperclip.copy(text)
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            # Fallback or re-raise? For now log and ignore to not crash app

    def paste(self) -> str:
        try:
            return pyperclip.paste()
        except Exception as e:
            logger.error(f"Failed to paste from clipboard: {e}")
            return ""

class LinuxNotificationAdapter(NotificationInterface):
    def notify(self, title: str, message: str) -> None:
        try:
            # Using notify-send as it is standard on most Linux DEs
            subprocess.run(
                ["notify-send", title, message],
                check=False,
                stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            logger.warning("notify-send not found, notification skipped")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
