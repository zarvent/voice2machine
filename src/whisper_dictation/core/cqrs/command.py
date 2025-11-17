"""
Módulo que define la clase base para todos los comandos de la aplicación.

En el patrón CQRS (Command Query Responsibility Segregation), un comando es un
objeto que encapsula la intención de cambiar el estado del sistema. No devuelve
datos, simplemente representa una solicitud para realizar una acción.
"""

from abc import ABC

class Command(ABC):
    """
    Clase base abstracta para los comandos.

    Todos los comandos específicos de la aplicación (ej. `StartRecordingCommand`)
    deben heredar de esta clase. Esto asegura que todos los comandos sigan
    un contrato común y puedan ser manejados por el `CommandBus`.
    """
    pass
