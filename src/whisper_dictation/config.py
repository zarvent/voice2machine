"""
Módulo para la carga y gestión de la configuración de la aplicación.

Este módulo es responsable de localizar y parsear el archivo `config.toml`
que se encuentra en la raíz del proyecto. Expone una única variable `config`
que contiene toda la configuración como un diccionario accesible.
"""

import toml
from pathlib import Path

# --- Ruta base del proyecto ---
# Se calcula la ruta al directorio raíz del proyecto para poder localizar
# el archivo de configuración de forma fiable sin importar desde dónde se
# ejecute la aplicación.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

def load_config():
    """
    Carga la configuración desde el archivo `config.toml`.

    Localiza el archivo en la raíz del proyecto y lo parsea utilizando la
    librería `toml`.

    Returns:
        Un diccionario que contiene toda la configuración de la aplicación.

    Raises:
        FileNotFoundError: Si el archivo `config.toml` no se encuentra en la
                           raíz del proyecto.
    """
    config_path = BASE_DIR / "config.toml"
    if not config_path.is_file():
        raise FileNotFoundError(f"el archivo de configuración no se encontró en {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return toml.load(f)

# --- Instancia global de la configuración ---
# Se carga la configuración una sola vez cuando se importa este módulo.
# Esto la convierte en un singleton accesible globalmente a través de
# `from whisper_dictation.config import config`.
config = load_config()
