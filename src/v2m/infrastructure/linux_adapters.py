import subprocess
import os
import time
from typing import Optional, Tuple
from v2m.core.interfaces import ClipboardInterface, NotificationInterface
from v2m.core.logging import logger


class LinuxClipboardAdapter(ClipboardInterface):
    """
    Adaptador de portapapeles para Linux que usa directamente xclip o wl-clipboard.

    No depende de PYPERCLIP para evitar problemas con variables de entorno
    en procesos daemon. Detecta automáticamente X11 vs Wayland.
    """

    def __init__(self):
        self._backend: Optional[str] = None
        self._env: dict = {}
        self._detect_environment()

    def _detect_environment(self) -> None:
        """
        Detecta si el sistema usa X11 o Wayland y obtiene las variables de entorno necesarias.
        """
        # Intentar obtener WAYLAND_DISPLAY primero (más moderno)
        wayland_display = os.environ.get("WAYLAND_DISPLAY")
        if wayland_display:
            self._backend = "wayland"
            self._env = {"WAYLAND_DISPLAY": wayland_display}
            logger.info("Clipboard backend: Wayland")
            return

        # Fallback a X11
        display = os.environ.get("DISPLAY")
        if display:
            self._backend = "x11"
            self._env = {"DISPLAY": display}
            logger.info("Clipboard backend: X11")
            return

        # Si no hay ninguna, intentar obtenerla de systemd/loginctl
        try:
            result = subprocess.run(
                ["loginctl", "show-session", "$(loginctl | grep $(whoami) | awk '{print $1}' | head -1)", "-p", "Display"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and "Display=" in result.stdout:
                display_value = result.stdout.strip().split("=", 1)[1]
                if display_value:
                    self._backend = "x11"
                    self._env = {"DISPLAY": display_value}
                    logger.info(f"Clipboard backend: X11 (from loginctl: {display_value})")
                    return
        except Exception as e:
            logger.warning(f"Could not detect display from loginctl: {e}")

        logger.warning("No DISPLAY or WAYLAND_DISPLAY found. Clipboard operations may fail.")
        self._backend = "x11"  # Default fallback
        self._env = {}

    def _get_clipboard_commands(self) -> Tuple[list, list]:
        """
        Retorna los comandos para copiar y pegar según el backend detectado.

        Returns:
            Tupla con (comando_copy, comando_paste)
        """
        if self._backend == "wayland":
            return (
                ["wl-copy"],
                ["wl-paste"]
            )
        else:  # x11
            return (
                ["xclip", "-selection", "clipboard"],
                ["xclip", "-selection", "clipboard", "-out"]
            )

    def copy(self, text: str) -> None:
        """
        Copia texto al portapapeles del sistema.

        Nota: xclip se queda en background esperando servir el clipboard.
        No esperamos al proceso, simplemente lo lanzamos y dejamos que el OS lo limpie.
        """
        if not text:
            return

        copy_cmd, _ = self._get_clipboard_commands()

        try:
            # Combinar env del sistema con las variables detectadas
            env = os.environ.copy()
            env.update(self._env)

            # Para xclip (y wl-copy similar), el proceso necesita quedarse en background
            # para servir el contenido del clipboard cuando otras apps lo soliciten.
            # Usamos Popen y NO esperamos al proceso.
            process = subprocess.Popen(
                copy_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                env=env
            )

            # Escribir el texto y cerrar stdin
            try:
                process.stdin.write(text.encode("utf-8"))
                process.stdin.close()

                # Esperar un momento mínimo para que xclip procese
                # Sin esto, lecturas inmediatas pueden obtener contenido antiguo
                time.sleep(0.05)  # 50ms
            except (BrokenPipeError, OSError) as e:
                logger.error(f"Failed to write to clipboard process: {e}")
                return

            # NO hacemos wait(). El proceso se queda en background sirviendo el clipboard.
            # El OS lo limpiará cuando sea necesario.
            logger.debug(f"Copied {len(text)} chars to clipboard (process PID: {process.pid})")

        except FileNotFoundError:
            logger.error(f"Clipboard tool not found: {copy_cmd[0]}. Install xclip or wl-clipboard.")
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")

    def paste(self) -> str:
        """
        Obtiene texto del portapapeles del sistema.

        Returns:
            Contenido del portapapeles o cadena vacía si falla.
        """
        _, paste_cmd = self._get_clipboard_commands()

        try:
            # Combinar env del sistema con las variables detectadas
            env = os.environ.copy()
            env.update(self._env)

            result = subprocess.run(
                paste_cmd,
                capture_output=True,
                env=env,
                timeout=2
            )

            if result.returncode != 0:
                logger.error(f"Clipboard paste failed: {result.stderr.decode('utf-8', errors='ignore')}")
                return ""

            return result.stdout.decode("utf-8", errors="ignore")

        except FileNotFoundError:
            logger.error(f"Clipboard tool not found: {paste_cmd[0]}. Install xclip or wl-clipboard.")
            return ""
        except subprocess.TimeoutExpired:
            logger.error("Clipboard paste operation timed out")
            return ""
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
