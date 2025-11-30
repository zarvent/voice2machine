"""Pruebas unitarias para el módulo de configuración.

Este módulo contiene las pruebas unitarias para verificar que el sistema
de configuración de v2m carga correctamente los valores desde el archivo
config.toml y los expone a través de la clase Settings.

Las pruebas verifican:
    - Carga correcta del modelo de Whisper configurado.
    - Configuración del idioma de transcripción.
    - Parámetros de reintentos para la API de Gemini.

Ejemplo de uso típico:
    pytest tests/unit/test_config.py -v
"""

import pytest
from v2m.config import Settings


def test_config_loading() -> None:
    """Verifica que la configuración se carga correctamente desde config.toml.

    Esta prueba asegura que los valores definidos en el archivo de
    configuración config.toml se cargan correctamente en la instancia
    de Settings y están disponibles para su uso en la aplicación.

    Returns:
        None

    Raises:
        AssertionError: Si el modelo de Whisper no coincide con 'large-v3-turbo'.
        AssertionError: Si el idioma de Whisper no es 'auto'.
        AssertionError: Si los reintentos de Gemini no son 3.
    """
    config = Settings()
    # El nombre del modelo debe coincidir con config.toml (actualmente large-v3-turbo)
    assert config.whisper.model == "large-v3-turbo"
    assert config.whisper.language == "auto"
    assert config.gemini.retry_attempts == 3
