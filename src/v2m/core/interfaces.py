"""
Interfaces abstractas para los adaptadores del sistema.

Este módulo define las interfaces (puertos) que deben implementar los
adaptadores de infraestructura para interactuar con el sistema operativo.
Siguiendo el principio de inversión de dependencias, la capa de aplicación
depende de estas abstracciones y no de implementaciones concretas.

Interfaces definidas:
    - ``ClipboardInterface``: Operaciones del portapapeles del sistema.
    - ``NotificationInterface``: Envío de notificaciones al escritorio.

Patrón utilizado:
    Estas interfaces forman parte del patrón Ports and Adapters (Hexagonal).
    Los "puertos" están aquí, y los "adaptadores" están en
    ``infrastructure/linux_adapters.py``.

Example:
    Inyección de dependencias en un handler::

        class MyHandler:
            def __init__(self, clipboard: ClipboardInterface):
                self.clipboard = clipboard

            def execute(self, text: str):
                self.clipboard.copy(text)
"""

from abc import ABC, abstractmethod

class ClipboardInterface(ABC):
    """Interfaz abstracta para operaciones del portapapeles del sistema.

    Define el contrato que deben cumplir los adaptadores de portapapeles
    para diferentes sistemas operativos o entornos gráficos (X11, Wayland).

    Esta interfaz permite desacoplar la lógica de negocio de la implementación
    específica del portapapeles, facilitando pruebas unitarias y portabilidad.

    Example:
        Implementación mock para pruebas::

            class MockClipboard(ClipboardInterface):
                def __init__(self):
                    self._content = ""

                def copy(self, text: str) -> None:
                    self._content = text

                def paste(self) -> str:
                    return self._content
    """
    @abstractmethod
    def copy(self, text: str) -> None:
        """Copia el texto proporcionado al portapapeles del sistema.

        El texto se almacena en el portapapeles y estará disponible para
        pegar en cualquier aplicación hasta que sea reemplazado por otro
        contenido.

        Args:
            text: El texto a copiar al portapapeles. Debe ser una cadena
                válida. Las cadenas vacías pueden ser ignoradas por algunas
                implementaciones.

        Note:
            La implementación debe manejar correctamente caracteres Unicode
            y saltos de línea.
        """
        pass

    @abstractmethod
    def paste(self) -> str:
        """Obtiene el contenido actual del portapapeles del sistema.

        Lee y retorna el texto actualmente almacenado en el portapapeles.
        Si el portapapeles contiene datos no textuales (imágenes, archivos),
        el comportamiento depende de la implementación.

        Returns:
            El texto contenido en el portapapeles. Retorna una cadena vacía
            si el portapapeles está vacío o contiene datos no textuales.

        Raises:
            Puede lanzar excepciones específicas de la implementación si
            hay problemas de acceso al portapapeles del sistema.
        """
        pass

class NotificationInterface(ABC):
    """Interfaz abstracta para el sistema de notificaciones del escritorio.

    Define el contrato para enviar notificaciones visuales al usuario.
    Las implementaciones pueden utilizar diferentes backends según el
    entorno (notify-send en Linux, toast en Windows, etc.).

    Las notificaciones son utilizadas para informar al usuario sobre el
    estado de las operaciones (grabación iniciada, transcripción completada,
    errores, etc.).

    Example:
        Implementación mock para pruebas::

            class MockNotification(NotificationInterface):
                def __init__(self):
                    self.notifications = []

                def notify(self, title: str, message: str) -> None:
                    self.notifications.append((title, message))
    """
    @abstractmethod
    def notify(self, title: str, message: str) -> None:
        """Envía una notificación visual al escritorio del usuario.

        Muestra un mensaje emergente utilizando el sistema de notificaciones
        del entorno de escritorio. La notificación aparece brevemente y
        luego desaparece automáticamente.

        Args:
            title: El título de la notificación. Debe ser breve y descriptivo.
                Ejemplos: "🎤 Grabando", "✅ Copiado", "❌ Error".
            message: El cuerpo del mensaje de la notificación. Puede incluir
                más detalles sobre la operación. Se recomienda limitar a
                80-100 caracteres para mejor legibilidad.

        Note:
            Las implementaciones deben manejar silenciosamente los errores
            (ej. si notify-send no está instalado) para no interrumpir
            el flujo principal de la aplicación.
        """
        pass
