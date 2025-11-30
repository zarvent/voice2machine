"""
Excepciones personalizadas del dominio de voice2machine.

Este módulo define la jerarquía de excepciones específicas de la aplicación.
Estas excepciones representan errores de negocio semánticos que permiten un
manejo de errores más granular y claro que las excepciones genéricas.

Jerarquía de excepciones:
    ::

        Exception
        └── ApplicationError (base para todas las excepciones de v2m)
            ├── MicrophoneNotFoundError
            ├── RecordingError
            ├── TranscriptionError
            └── LLMError

Beneficios de excepciones personalizadas:
    - **Granularidad**: Manejo diferenciado por tipo de error.
    - **Semántica**: Los nombres describen el problema de negocio.
    - **Encapsulamiento**: No filtran detalles de infraestructura.
    - **Captura grupal**: ``except ApplicationError`` captura todos.

Example:
    Manejo de errores en un handler::

        from v2m.domain.errors import TranscriptionError, LLMError

        try:
            transcription = service.transcribe(audio)
        except TranscriptionError as e:
            logger.error(f"Fallo en transcripción: {e}")
            notification.notify("❌ Error", "No se pudo transcribir")
"""

class ApplicationError(Exception):
    """Clase base para todas las excepciones personalizadas de la aplicación.

    Heredar de una clase base común permite capturar todos los errores de
    negocio conocidos con un solo bloque ``except ApplicationError``,
    mientras se dejan pasar errores inesperados del sistema.

    Example:
        Captura genérica de errores de aplicación::

            try:
                await handler.execute(command)
            except ApplicationError as e:
                # Error conocido de negocio
                return f"ERROR: {e}"
            except Exception as e:
                # Error inesperado del sistema
                logger.critical(f"Error no manejado: {e}")
                raise
    """
    pass

class MicrophoneNotFoundError(ApplicationError):
    """Excepción lanzada cuando no se detecta ningún micrófono funcional.

    Esta excepción indica que el dispositivo de grabación de audio por defecto
    no está disponible, no está conectado, o no está configurado correctamente
    en el sistema operativo.

    Causas comunes:
        - Micrófono USB desconectado.
        - Permisos insuficientes para acceder al dispositivo de audio.
        - Dispositivo de entrada por defecto mal configurado en PulseAudio/ALSA.
        - Driver de audio no cargado.

    Solución sugerida:
        Verificar con ``pactl list sources`` o ``arecord -l`` que el
        micrófono esté visible para el sistema.
    """
    pass

class RecordingError(ApplicationError):
    """Excepción lanzada cuando ocurre un error durante la grabación de audio.

    Cubre errores relacionados con la captura de audio, desde el inicio
    de la grabación hasta la obtención de los datos del buffer.

    Causas comunes:
        - Intento de iniciar una grabación cuando ya hay una en progreso.
        - Intento de detener cuando no hay grabación activa.
        - Fallo del stream de sounddevice.
        - Buffer de audio vacío (grabación de duración cero).
        - Permisos de acceso al dispositivo de audio revocados.

    Atributos heredados:
        args[0]: Mensaje descriptivo del error específico.
    """
    pass

class TranscriptionError(ApplicationError):
    """Excepción lanzada cuando falla el proceso de transcripción.

    Indica un problema durante la conversión de audio a texto usando el
    modelo Whisper. El audio ya fue capturado exitosamente pero no pudo
    ser procesado.

    Causas comunes:
        - Modelo Whisper corrupto o no descargado completamente.
        - Memoria GPU insuficiente para cargar el modelo.
        - Formato de audio inválido o corrupto.
        - Error de CTranslate2/CUDA durante la inferencia.
        - Timeout en la transcripción (audio demasiado largo).

    Diagnóstico:
        Verificar logs para el mensaje de error específico de faster-whisper
        o ctranslate2.
    """
    pass

class LLMError(ApplicationError):
    """Excepción lanzada cuando hay un error en la comunicación con el LLM.

    Encapsula errores relacionados con el servicio de modelo de lenguaje
    (actualmente Google Gemini), incluyendo problemas de red, autenticación
    y límites de uso.

    Causas comunes:
        - API key inválida, expirada o sin permisos.
        - Error de red o timeout en la conexión.
        - Rate limiting (demasiadas solicitudes).
        - Respuesta vacía o malformada del servicio.
        - Servicio de Gemini no disponible.

    Note:
        El sistema tiene un fallback que, si falla el LLM, copia el texto
        original sin refinar al portapapeles.

    Diagnóstico:
        Verificar que ``GEMINI_API_KEY`` esté correctamente configurada en
        el archivo ``.env`` y que la cuenta tenga créditos disponibles.
    """
    pass
