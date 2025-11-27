"""
modulo que define la clase base para todos los comandos de la aplicacion.

en el patron cqrs (command query responsibility segregation), un comando es un
objeto que encapsula la intencion de cambiar el estado del sistema. no devuelve
datos, simplemente representa una solicitud para realizar una accion.
"""

from abc import ABC

class Command(ABC):
    """
    clase base abstracta para los comandos.

    todos los comandos especificos de la aplicacion (ej `startrecordingcommand`)
    deben heredar de esta clase. esto asegura que todos los comandos sigan
    un contrato comun y puedan ser manejados por el `commandbus`.
    """
    pass
