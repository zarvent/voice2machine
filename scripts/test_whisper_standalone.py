#!/usr/bin/env python3
"""
Prueba completa del pipeline de transcripción

¿Para qué sirve?
    Este script prueba TODO el proceso de transcripción de principio
    a fin, sin necesidad de hablar. Genera audio de prueba (silencio)
    y verifica que Whisper pueda procesarlo.

¿Cuándo usarlo?
    - Después de instalar V2M
    - Después de actualizar dependencias
    - Cuando la transcripción falla y no sabes por qué
    - Para verificar que CUDA funciona antes de usar V2M

¿Cómo lo uso?
    $ python scripts/test_whisper_standalone.py

¿Qué debería ver?
    1. Verificando entorno...
    LD_LIBRARY_PATH: /ruta/a/nvidia/libs
    2. Generando audio dummy (1 segundo de silencio)...
    3. Cargando modelo (device=cuda)...
    ✅ Modelo cargado en CUDA
    4. Transcribiendo...
    Detected language: es
    ✅ Transcripción completada

¿Qué pasa si CUDA falla?
    El script automáticamente intenta usar CPU. Verás:

    ❌ Falló carga en CUDA: [error]
    Intentando CPU...
    ⚠️ Modelo cargado en CPU (Fallback)

    Funciona, pero será más lento. Para arreglar CUDA:
    $ ./scripts/repair_libs.sh

¿Por qué usa el modelo "tiny"?
    Para que la prueba sea rápida (~5 segundos). En producción,
    V2M usa "large-v2" que es mucho más preciso pero más pesado.

Para desarrolladores:
    El audio dummy es un array numpy de ceros (silencio) de 1 segundo
    a 16kHz. faster-whisper espera audio como numpy array float32.
"""

import os
import sys
import numpy as np
from faster_whisper import WhisperModel
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_whisper")


def test_transcription() -> None:
    """
    Prueba el pipeline completo: entorno → modelo → transcripción.

    Genera audio de silencio y lo pasa por Whisper para verificar
    que todo funcione. Si CUDA falla, intenta con CPU automáticamente.

    El proceso:
        1. Verifica que LD_LIBRARY_PATH esté configurado.
        2. Genera 1 segundo de audio silencioso.
        3. Carga Whisper (primero CUDA, luego CPU como fallback).
        4. Ejecuta una transcripción de prueba.

    Note:
        El audio de silencio no producirá texto, pero permite
        verificar que todo el pipeline funcione correctamente.
    """
    print("1. Verificando entorno...")
    print(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH', 'Not Set')}")

    print("2. Generando audio dummy (1 segundo de silencio)...")
    # Generar 1 segundo de silencio a 16kHz
    audio = np.zeros(16000, dtype=np.float32)

    print("3. Cargando modelo (device=cuda)...")
    try:
        model = WhisperModel("tiny", device="cuda", compute_type="float16")
        print("✅ Modelo cargado en CUDA")
    except Exception as e:
        print(f"❌ Falló carga en CUDA: {e}")
        print("Intentando CPU...")
        try:
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            print("⚠️ Modelo cargado en CPU (Fallback)")
        except Exception as e2:
            print(f"❌ Falló carga en CPU también: {e2}")
            return

    print("4. Transcribiendo...")
    try:
        segments, info = model.transcribe(audio, beam_size=5)
        print(f"Detected language: {info.language}")
        for segment in segments:
            print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
        print("✅ Transcripción completada")
    except Exception as e:
        print(f"❌ Error durante transcripción: {e}")

if __name__ == "__main__":
    test_transcription()
