# This file is part of voice2machine.
#
# voice2machine is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Pruebas unitarias del servicio de detección de actividad vocal (VAD).

Propósito
---------
Verificar el correcto funcionamiento de VADService, el componente que
identifica y extrae segmentos de audio que contienen voz humana.

Fundamento teórico
------------------
VAD (Voice Activity Detection) es una técnica de procesamiento de señales
que discrimina entre segmentos de voz y no-voz en una señal de audio.

En v2m, VAD cumple un rol de optimización crítico:
    * Reduce el audio enviado a transcripción (solo voz, no silencios).
    * Disminuye latencia y costos de API.
    * Mejora la calidad de transcripción al eliminar ruido.

Implementación
--------------
Usamos Silero VAD, un modelo de deep learning basado en redes neuronales
recurrentes (LSTM). Características:
    * Tamaño: ~2MB (muy liviano para un modelo de ML)
    * Latencia: <1ms por frame en CPU
    * Precisión: >95% en datasets estándar

El parámetro clave es el "threshold" (umbral), un valor entre 0 y 1 que
controla la sensibilidad:
    * threshold bajo (0.3): Más sensible, detecta susurros, más falsos positivos.
    * threshold alto (0.7): Más estricto, solo voz clara, puede perder audio.
    * threshold medio (0.5): Balance típico para la mayoría de casos.

Este archivo verifica
---------------------
    * Manejo correcto de casos edge (audio vacío, sin voz).
    * Extracción correcta de segmentos de voz.
    * Uso del threshold desde configuración (no hardcodeado).

Estrategia de testing
---------------------
Mockeamos el modelo Silero para:
    * Evitar descargas de ~40MB en cada ejecución.
    * Garantizar determinismo (el modelo real puede variar).
    * Reducir tiempo de ejecución de minutos a milisegundos.

Referencias
-----------
    * Silero VAD: https://github.com/snakers4/silero-vad
    * Teoría VAD: Ramirez, J. et al. "Voice Activity Detection" (2007)

Ejecución
---------
    >>> pytest tests/unit/test_vad_service.py -v
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from v2m.infrastructure.vad_service import VADService


@pytest.fixture
def vad_service() -> VADService:
    """Fixture que proporciona una instancia base de VADService.

    Las fixtures en pytest son funciones que proveen objetos reutilizables
    para las pruebas. Se ejecutan antes de cada test que las solicite.

    Ventajas sobre setUp():
        * Inyección de dependencias declarativa.
        * Reutilización entre archivos de test.
        * Soporte para scopes (function, class, module, session).

    Returns:
        VADService: Instancia sin modificaciones, tal como se usaría
            en producción. Útil para tests que necesitan el comportamiento
            real (con cuidado de no cargar el modelo).
    """
    return VADService()


@pytest.fixture
def configured_vad_service() -> VADService:
    """Fixture que proporciona VADService con modelo mockeado.

    Esta fixture resuelve el problema de las dependencias pesadas:
    el modelo Silero VAD real requiere PyTorch y pesa ~40MB. Para
    pruebas unitarias, reemplazamos estas dependencias con mocks.

    Test doubles utilizados (taxonomía de Meszaros):
        * Stub: get_speech_timestamps retorna valores predefinidos.
        * Dummy: model es un objeto que solo necesita existir (no ser None).

    ¿Por qué no cargar el modelo real?
        1. Velocidad: Las pruebas deben correr en segundos, no minutos.
        2. Aislamiento: Probamos la lógica de VADService, no el modelo.
        3. CI/CD: Los runners no siempre tienen GPU o PyTorch configurado.

    Returns:
        VADService: Instancia con load_model y model mockeados,
            lista para pruebas rápidas y deterministas.
    """
    service = VADService()
    service.load_model = MagicMock()
    service.model = MagicMock()  # process() valida que model != None
    return service


def test_vad_process_empty_audio(vad_service: VADService) -> None:
    """Verifica el manejo robusto de audio vacío.

    Caso de prueba (edge case)
    --------------------------
    Entrada: Array de audio con 0 muestras.
    Salida esperada: Array vacío, sin excepciones.

    Escenarios reales donde esto ocurre
    -----------------------------------
        * Usuario presiona grabar/detener instantáneamente.
        * Error en el driver de audio que retorna buffer vacío.
        * Bug en código cliente que pasa datos incorrectos.

    Principio de diseño: Robustez
    -----------------------------
    Siguiendo el principio de Postel ("sé conservador en lo que envías,
    liberal en lo que aceptas"), el servicio debe manejar graciosamente
    entradas inválidas en lugar de fallar catastróficamente.

    Args:
        vad_service: Fixture que provee instancia de VADService.

    Raises:
        AssertionError: Si el resultado no es un array de tamaño 0.
    """
    # Configuramos mocks para evitar carga del modelo real
    vad_service.load_model = MagicMock()
    vad_service.get_speech_timestamps = MagicMock(return_value=[])

    # Audio vacío: tensor de shape (0,)
    empty_audio = np.array([], dtype=np.float32)

    # Act
    result = vad_service.process(empty_audio)

    # Assert: resultado debe ser vacío, no excepción
    assert result.size == 0, "Audio vacío debe retornar resultado vacío"


def test_vad_process_no_speech(configured_vad_service: VADService) -> None:
    """Verifica que el silencio no se detecte como voz.

    Caso de prueba (condición de borde)
    -----------------------------------
    Entrada: 1 segundo de silencio absoluto (16000 muestras de valor 0).
    Salida esperada: Array vacío (no hay voz que extraer).

    ¿Por qué 16000 muestras?
    ------------------------
    Trabajamos con sample rate de 16kHz (16000 Hz), el estándar de facto
    para procesamiento de voz. Es suficiente para capturar frecuencias
    hasta 8kHz (teorema de Nyquist), cubriendo el rango vocal humano.

    Frecuencias de voz humana:
        * Fundamentales: 85-255 Hz
        * Formantes: hasta ~4000 Hz
        * 16kHz captura todo esto con margen

    Args:
        configured_vad_service: Fixture con modelo mockeado.

    Raises:
        AssertionError: Si detecta voz en audio silencioso.
    """
    # El mock simula que VAD no encontró segmentos de voz
    configured_vad_service.get_speech_timestamps = MagicMock(return_value=[])

    # 1 segundo de silencio digital (todos los valores en 0)
    audio = np.zeros(16000, dtype=np.float32)

    # Act
    result = configured_vad_service.process(audio)

    # Assert
    assert result.size == 0, "Silencio no debe producir segmentos de voz"


def test_vad_process_with_speech(configured_vad_service: VADService) -> None:
    """Verifica la extracción correcta de segmentos de voz.

    Caso de prueba (camino feliz)
    -----------------------------
    Entrada: Audio con dos segmentos de voz intercalados con silencio.
    Salida esperada: Concatenación de ambos segmentos.

    Diagrama del escenario
    ----------------------
    Muestra:    0    1000   2000   3000   4000   5000
                |     |      |      |      |      |
    Audio:      [  silencio  ][VOZ_A][silencio][VOZ_B][fin]
    Detectado:              ↑______↑        ↑______↑
    Resultado:              [  VOZ_A  +  VOZ_B  ]

    El servicio debe:
        1. Identificar los timestamps de inicio/fin de cada segmento.
        2. Extraer las muestras correspondientes del audio original.
        3. Concatenarlas en orden cronológico.

    Cálculo de tamaño esperado
    --------------------------
    Segmento A: muestras 1000-2000 = 1000 muestras
    Segmento B: muestras 3000-4000 = 1000 muestras
    Total: 2000 muestras

    Args:
        configured_vad_service: Fixture con modelo mockeado.

    Raises:
        AssertionError: Si el tamaño o contenido no coinciden.
    """
    # Configuramos el mock para simular detección de 2 segmentos
    configured_vad_service.get_speech_timestamps = MagicMock(return_value=[
        {'start': 1000, 'end': 2000},  # Segmento A
        {'start': 3000, 'end': 4000}   # Segmento B
    ])

    # Creamos audio con valores únicos para verificar extracción correcta
    # audio[i] = i, así podemos validar que se extrajeron las muestras correctas
    audio = np.arange(5000, dtype=np.float32)

    # Act
    result = configured_vad_service.process(audio)

    # Assert: tamaño correcto
    assert result.size == 2000, (
        f"Esperaba 2000 muestras, obtuve {result.size}"
    )

    # Assert: contenido correcto (muestras específicas extraídas)
    expected = np.concatenate([audio[1000:2000], audio[3000:4000]])
    np.testing.assert_array_equal(
        result, expected,
        err_msg="El contenido extraído no coincide con los segmentos esperados"
    )


def test_vad_uses_configured_threshold(configured_vad_service: VADService) -> None:
    """Verifica que el threshold provenga de la configuración, no del código.

    Caso de prueba (regression test)
    --------------------------------
    Este test documenta y previene la regresión de un bug específico:
    anteriormente, el threshold estaba hardcodeado a 0.5 en el código.

    El problema del hardcoding
    --------------------------
    Un threshold fijo ignora las necesidades del usuario:
        * Ambiente ruidoso → necesita threshold más alto
        * Grabación de susurros → necesita threshold más bajo
        * Diferentes micrófonos → sensibilidades distintas

    La solución
    -----------
    El threshold se lee de config.whisper.vad_parameters.threshold,
    permitiendo ajustes sin modificar código fuente.

    ¿Qué es el threshold?
    ---------------------
    Es la probabilidad mínima (0-1) para considerar un frame como voz:

        P(voz) >= threshold → es voz
        P(voz) <  threshold → no es voz

    Valores típicos:
        * 0.3: Alta sensibilidad (captura más, más falsos positivos)
        * 0.5: Balance estándar
        * 0.7: Alta especificidad (menos falsos positivos, puede perder audio)

    Args:
        configured_vad_service: Fixture con modelo mockeado.

    Raises:
        AssertionError: Si el servicio usa un threshold diferente al
            configurado (indicaría que está hardcodeado).
    """
    configured_vad_service.get_speech_timestamps = MagicMock(return_value=[
        {'start': 0, 'end': 1000}
    ])

    audio = np.arange(1000, dtype=np.float32)

    # Mockeamos el config para inyectar un threshold específico
    with patch('v2m.infrastructure.vad_service.config') as mock_config:
        # Usamos 0.7 (diferente al default 0.5) para detectar hardcoding
        mock_config.whisper.vad_parameters.threshold = 0.7

        configured_vad_service.process(audio)

        # Verificamos que se usó el valor del config
        call_args = configured_vad_service.get_speech_timestamps.call_args
        actual_threshold = call_args.kwargs.get('threshold')

        assert actual_threshold == 0.7, (
            f"Threshold incorrecto: {actual_threshold}. "
            "El servicio debe usar el valor de config (0.7), no uno hardcodeado."
        )
