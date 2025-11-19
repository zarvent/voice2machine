"""
módulo de configuración para el logging estructurado de la aplicación

utilizamos un logging estructurado en formato JSON para facilitar la búsqueda
el filtrado y el análisis de logs especialmente en entornos de producción o
cuando se integran con sistemas de recolección de logs
"""

import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """
    configura y devuelve un logger estructurado (JSON)

    el logger se nombra 'v2m' y se configura para emitir logs
    a partir del nivel INFO los logs se envían a la salida estándar (stdout)

    el formato JSON incluye timestamp nombre del logger nivel y mensaje

    returns:
        una instancia del logger configurado
    """
    logger = logging.getLogger("v2m")
    logger.setLevel(logging.INFO)

    # previene que se añadan múltiples handlers si este módulo se importa más de una vez
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- configuración del handler y el formatter ---
    # se utiliza un streamhandler para enviar logs a stdout
    handler = logging.StreamHandler(sys.stdout)
    # se usa jsonformatter para asegurar que todos los logs sean objetos JSON
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
