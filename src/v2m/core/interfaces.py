from abc import ABC, abstractmethod

class ClipboardInterface(ABC):
     """
    interfaz abstracta para operaciones del portapapeles.

    define los metodos necesarios para interactuar con el portapapeles del sistema,
    permitiendo copiar y pegar texto.
    """
    @abstractmethod
    def copy(self, text: str) -> None:
        """
        copia el texto proporcionado al portapapeles del sistema.

        args:
            text (str): el texto a copiar.
        """
        pass

    @abstractmethod
    def paste(self) -> str:
        """
        obtiene el contenido actual del portapapeles del sistema.

        returns:
            str: el texto contenido en el portapapeles.
        """
        pass

class NotificationInterface(ABC):
    """
    interfaz abstracta para el sistema de notificaciones.

    define los metodos para enviar notificaciones visuales al usuario.
    """
    @abstractmethod
    def notify(self, title: str, message: str) -> None:
        """
        envia una notificacion al sistema.

        args:
            title (str): el titulo de la notificacion.
            message (str): el cuerpo del mensaje de la notificacion.
        """
        pass
