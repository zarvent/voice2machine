"""
módulo que define la clase base para todos los comandos de la aplicación

en el patrón CQRS (command query responsibility segregation) un comando es un
objeto que encapsula la intención de cambiar el estado del sistema no devuelve
datos simplemente representa una solicitud para realizar una acción
"""

from abc import ABC

class Command(ABC):
    """
    clase base abstracta para los comandos

    todos los comandos específicos de la aplicación (ej `startrecordingcommand`)
    deben heredar de esta clase esto asegura que todos los comandos sigan
    un contrato común y puedan ser manejados por el `commandbus`
    """
    pass
