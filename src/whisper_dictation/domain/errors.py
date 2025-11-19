"""
módulo que define las excepciones personalizadas del dominio de la aplicación

estas excepciones representan errores de negocio específicos y semánticos
lo que permite un manejo de errores más granular y claro en la capa de aplicación
en comparación con el uso de excepciones genéricas
"""

class ApplicationError(Exception):
    """
    clase base para todas las excepciones personalizadas de la aplicación

    heredar de una clase base común permite capturar todos los errores de
    negocio conocidos con un solo bloque `except applicationerror`
    """
    pass

class MicrophoneNotFoundError(ApplicationError):
    """
    excepción lanzada cuando no se detecta ningún micrófono funcional

    esto puede ocurrir si el dispositivo de grabación por defecto no está
    disponible o no está configurado correctamente en el sistema
    """
    pass

class RecordingError(ApplicationError):
    """
    excepción lanzada cuando ocurre un error durante la grabación de audio

    puede ser causada por problemas con `ffmpeg` o con los permisos de acceso
    al dispositivo de audio
    """
    pass

class TranscriptionError(ApplicationError):
    """
    excepción lanzada cuando falla el proceso de transcripción

    esto podría deberse a un modelo de WHISPER corrupto problemas de memoria
    de la GPU o un formato de audio inválido
    """
    pass

class LLMError(ApplicationError):
    """
    excepción lanzada cuando hay un error en la comunicación con el LLM

    puede ser causada por una clave de API inválida problemas de red o
    errores internos del servicio del LLM
    """
    pass
