"""
Clase base abstracta para comandos del patrón CQRS.

Este módulo define la clase base ``Command`` de la cual heredan todos los
comandos específicos de la aplicación. En el patrón CQRS (Command Query
Responsibility Segregation), un comando representa la intención de modificar
el estado del sistema.

Características de los comandos:
    - Representan acciones, no consultas.
    - Son objetos de datos inmutables (idealmente).
    - No contienen lógica de negocio, solo datos.
    - Son procesados por exactamente un ``CommandHandler``.

Flujo de un comando:
    1. Se crea una instancia del comando con los datos necesarios.
    2. Se envía al ``CommandBus`` mediante ``dispatch()``.
    3. El bus localiza el handler registrado para ese tipo de comando.
    4. El handler ejecuta la lógica de negocio correspondiente.

Example:
    Definir un comando personalizado::

        from v2m.core.cqrs.command import Command

        class EnviarEmailCommand(Command):
            def __init__(self, destinatario: str, asunto: str):
                self.destinatario = destinatario
                self.asunto = asunto
"""

from abc import ABC

class Command(ABC):
    """Clase base abstracta para todos los comandos de la aplicación.

    Todos los comandos específicos (ej. ``StartRecordingCommand``,
    ``StopRecordingCommand``) deben heredar de esta clase. Esto garantiza
    que todos los comandos sigan un contrato común y puedan ser despachados
    por el ``CommandBus``.

    La clase es intencionalmente vacía (marker class) ya que su propósito
    es proporcionar un tipo base común para el sistema de tipos y el
    despacho polimórfico.

    Example:
        Comando sin datos adicionales::

            class PingCommand(Command):
                pass

        Comando con datos::

            class CrearUsuarioCommand(Command):
                def __init__(self, nombre: str, email: str):
                    self.nombre = nombre
                    self.email = email
    """
    pass
