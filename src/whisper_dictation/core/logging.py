"""
Módulo de configuración para el logging estructurado de la aplicación.

Utilizamos un logging estructurado en formato JSON para facilitar la búsqueda,
el filtrado y el análisis de logs, especialmente en entornos de producción o
cuando se integran con sistemas de recolección de logs.
"""

import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """
    Configura y devuelve un logger estructurado (JSON).

    El logger se nombra 'whisper_dictation' y se configura para emitir logs
    a partir del nivel INFO. Los logs se envían a la salida estándar (stdout).

    El formato JSON incluye timestamp, nombre del logger, nivel y mensaje.

    Returns:
        Una instancia del logger configurado.
    """
    logger = logging.getLogger("whisper_dictation")
    logger.setLevel(logging.INFO)

    # Previene que se añadan múltiples handlers si este módulo se importa más de una vez.
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- Configuración del handler y el formatter ---
    # Se utiliza un StreamHandler para enviar logs a stdout.
    handler = logging.StreamHandler(sys.stdout)
    # Se usa JsonFormatter para asegurar que todos los logs sean objetos JSON.
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

# --- Instancia global del logger ---
# Se crea una única instancia del logger que será accesible desde toda la
# aplicación, asegurando una configuración consistente.
logger = setup_logging()
