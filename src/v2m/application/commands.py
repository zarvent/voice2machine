"""
modulo que define los comandos especificos de la aplicacion.

cada clase en este modulo representa una intencion de accion que el sistema
puede realizar. estos objetos son despachados por el `commandbus` y no
contienen logica de negocio, solo los datos necesarios para ejecutar la accion.
"""

from v2m.core.cqrs.command import Command

class StartRecordingCommand(Command):
    """
    comando para iniciar la grabacion de audio.

    este comando no requiere datos adicionales. al ser despachado, instruye
    al sistema para que comience a capturar audio del microfono.
    """
    pass

class StopRecordingCommand(Command):
    """
    comando para detener la grabacion y solicitar la transcripcion.

    este comando tampoco requiere datos. su funcion es finalizar la grabacion
    actual y disparar el proceso de transcripcion del audio capturado.
    """
    pass

class ProcessTextCommand(Command):
    """
    comando para procesar y refinar un bloque de texto usando un llm.

    este comando encapsula el texto que necesita ser procesado.
    """
    def __init__(self, text: str) -> None:
        """
        inicializa el comando con el texto a procesar.

        args:
            text (str): el texto que sera enviado al servicio de llm para su refinamiento.
        """
        self.text = text
