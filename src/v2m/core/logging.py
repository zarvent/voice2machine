"""
modulo de configuracion para el logging estructurado de la aplicacion.

utilizamos un logging estructurado en formato json para facilitar la busqueda,
el filtrado y el analisis de logs, especialmente en entornos de produccion o
cuando se integran con sistemas de recoleccion de logs.
"""

import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """
    configura y devuelve un logger estructurado (json).

    el logger se nombra 'v2m' y se configura para emitir logs
    a partir del nivel info. los logs se envian a la salida estandar (stdout).

    el formato json incluye timestamp, nombre del logger, nivel y mensaje.

    returns:
        logging.Logger: una instancia del logger configurado.
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
