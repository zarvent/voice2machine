"""
configuración de logging estructurado en formato json para voice2machine

este módulo configura un sistema de logging estructurado que emite
registros en formato json facilitando el análisis automatizado búsqueda
y agregación de logs en sistemas de monitoreo

características
    - formato json para cada entrada de log
    - incluye timestamp nivel nombre del logger y mensaje
    - salida a stdout para compatibilidad con systemd/journald
    - instancia global pre-configurada para uso en toda la aplicación

formato de salida
    cada línea es un objeto json independiente::

        {"asctime": "2024-01-15 10:30:45", "name": "v2m", "levelname": "INFO",
         "message": "grabación iniciada"}

uso
    importar el logger global desde cualquier módulo::

        from v2m.core.logging import logger

        logger.info("Operación completada")
        logger.error(f"Error: {e}")
        logger.debug("Datos de depuración")

note
    el nivel por defecto es INFO los mensajes DEBUG no se mostrarán
    a menos que se modifique el nivel del logger
"""

import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging() -> logging.Logger:
    """
    configura y retorna un logger estructurado en formato json

    crea un logger nombrado 'v2m' configurado para emitir mensajes de nivel
    INFO o superior a stdout en formato json si el módulo se importa
    múltiples veces evita duplicar handlers

    el formato json incluye los siguientes campos
        - ``asctime`` timestamp iso del evento
        - ``name`` nombre del logger (siempre 'v2m')
        - ``levelname`` nivel del mensaje (INFO WARNING ERROR etc)
        - ``message`` contenido del mensaje de log

    returns:
        una instancia de ``logging.Logger`` configurada y lista para usar
        todos los módulos deberían importar la instancia global ``logger``
        en lugar de llamar esta función directamente

    example
        configuración automática al importar::

            from v2m.core.logging import logger
            logger.info("Aplicación iniciada")
    """
    logger = logging.getLogger("v2m")
    logger.setLevel(logging.INFO)

    # previene que se anadan multiples handlers si este modulo se importa mas de una vez
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- configuracion del handler y el formatter ---
    # se utiliza un streamhandler para enviar logs a stdout
    handler = logging.StreamHandler(sys.stdout)
    # se usa jsonformatter para asegurar que todos los logs sean objetos json
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

# --- instancia global del logger ---
# se crea una única instancia del logger que será accesible desde toda la
# aplicación asegurando una configuración consistente
logger = setup_logging()
