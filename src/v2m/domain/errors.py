"""
modulo que define las excepciones personalizadas del dominio de la aplicacion.

estas excepciones representan errores de negocio especificos y semanticos,
lo que permite un manejo de errores mas granular y claro en la capa de aplicacion
en comparacion con el uso de excepciones genericas.
"""

class ApplicationError(Exception):
    """
    clase base para todas las excepciones personalizadas de la aplicacion.

    heredar de una clase base comun permite capturar todos los errores de
    negocio conocidos con un solo bloque `except applicationerror`.
    """
    pass

class MicrophoneNotFoundError(ApplicationError):
    """
    excepcion lanzada cuando no se detecta ningun microfono funcional.

    esto puede ocurrir si el dispositivo de grabacion por defecto no esta
    disponible o no esta configurado correctamente en el sistema.
    """
    pass

class RecordingError(ApplicationError):
    """
    excepcion lanzada cuando ocurre un error durante la grabacion de audio.

    puede ser causada por problemas con `ffmpeg` o con los permisos de acceso
    al dispositivo de audio.
    """
    pass

class TranscriptionError(ApplicationError):
    """
    excepcion lanzada cuando falla el proceso de transcripcion.

    esto podria deberse a un modelo de whisper corrupto, problemas de memoria
    de la gpu o un formato de audio invalido.
    """
    pass

class LLMError(ApplicationError):
    """
    excepcion lanzada cuando hay un error en la comunicacion con el llm.

    puede ser causada por una clave de api invalida, problemas de red o
    errores internos del servicio del llm.
    """
    pass
