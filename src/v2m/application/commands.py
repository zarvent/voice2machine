# This file is part of voice2machine.
#
# voice2machine is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""
módulo que define los comandos específicos de la aplicación

cada clase en este módulo representa una intención de acción que el sistema
puede realizar estos objetos son despachados por el `commandbus` y no
contienen lógica de negocio solo los datos necesarios para ejecutar la acción
"""

from v2m.core.cqrs.command import Command

class StartRecordingCommand(Command):
    """
    comando para iniciar la grabación de audio

    este comando no requiere datos adicionales al ser despachado instruye
    al sistema para que comience a capturar audio del micrófono
    """
    pass

class StopRecordingCommand(Command):
    """
    comando para detener la grabación y solicitar la transcripción

    este comando tampoco requiere datos su función es finalizar la grabación
    actual y disparar el proceso de transcripción del audio capturado
    """
    pass

class ProcessTextCommand(Command):
    """
    comando para procesar y refinar un bloque de texto usando un llm

    este comando encapsula el texto que necesita ser procesado
    """
    def __init__(self, text: str) -> None:
        """
        inicializa el comando con el texto a procesar

        args:
            text: el texto que será enviado al servicio de llm para su refinamiento
        """
        self.text = text
