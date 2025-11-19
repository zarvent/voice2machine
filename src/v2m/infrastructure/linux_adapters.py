import subprocess
import pyperclip
from v2m.core.interfaces import ClipboardInterface, NotificationInterface
from v2m.core.logging import logger

class LinuxClipboardAdapter(ClipboardInterface):
    def copy(self, text: str) -> None:
        try:
            pyperclip.copy(text)
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            # fallback o relanzar por ahora registrar e ignorar para no bloquear la aplicación

    def paste(self) -> str:
        try:
            return pyperclip.paste()
        except Exception as e:
            logger.error(f"Failed to paste from clipboard: {e}")
            return ""

class LinuxNotificationAdapter(NotificationInterface):
    def notify(self, title: str, message: str) -> None:
        try:
            # usando notify-send ya que es estándar en la mayoría de los de de linux
            subprocess.run(
                ["notify-send", title, message],
                check=False,
                stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            logger.warning("notify-send not found, notification skipped")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
