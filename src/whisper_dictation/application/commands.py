"""
Módulo que define los comandos específicos de la aplicación.

Cada clase en este módulo representa una intención de acción que el sistema
puede realizar. Estos objetos son despachados por el `CommandBus` y no
contienen lógica de negocio, solo los datos necesarios para ejecutar la acción.
"""

from whisper_dictation.core.cqrs.command import Command

class StartRecordingCommand(Command):
    """
    Comando para iniciar la grabación de audio.

    Este comando no requiere datos adicionales. Al ser despachado, instruye
    al sistema para que comience a capturar audio del micrófono.
    """
    pass

class StopRecordingCommand(Command):
    """
    Comando para detener la grabación y solicitar la transcripción.

    Este comando tampoco requiere datos. Su función es finalizar la grabación
    actual y disparar el proceso de transcripción del audio capturado.
    """
    pass

class ProcessTextCommand(Command):
    """
    Comando para procesar y refinar un bloque de texto usando un LLM.

    Este comando encapsula el texto que necesita ser procesado.
    """
    def __init__(self, text: str) -> None:
        """
        Inicializa el comando con el texto a procesar.

        Args:
            text (str): El texto que será enviado al servicio de LLM para su refinamiento.
        """
        self.text = text
