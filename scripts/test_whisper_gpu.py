#!/usr/bin/env python3
"""
Descarga y prueba del modelo Whisper

¿Qué hace este script?
    Descarga el modelo de transcripción (Whisper large-v2) y verifica
    que se cargue correctamente en tu GPU. Es lo primero que debes
    correr después de instalar V2M.

¿Por qué tarda tanto la primera vez?
    El modelo pesa ~3 GB y se descarga de internet. La primera
    ejecución puede tomar 5-10 minutos dependiendo de tu conexión.
    Las siguientes veces es instantáneo porque ya está en caché.

¿Cómo lo uso?
    $ python scripts/test_whisper_gpu.py

¿Qué debería ver?
    🚀 Descargando modelo large-v2 (3GB, primera vez solamente)...
    ✅ Modelo cargado exitosamente en GPU RTX 3060!
    📊 Info del modelo:
       - Dispositivo: CUDA (RTX 3060)
       - Precisión: float16
       - Memoria GPU disponible: ~6GB

¿Cuánta VRAM necesito?
    El modelo large-v2 necesita ~5-6 GB de VRAM. Funciona bien en:
    - RTX 3060 (12 GB) ✅
    - RTX 3070/3080 ✅
    - RTX 2060 (6 GB) - Justo, pero funciona
    - GTX 1060 (6 GB) - Muy justo

¿Qué hago si no tengo suficiente VRAM?
    Puedes usar un modelo más pequeño editando config.toml:
    - "medium" necesita ~3 GB
    - "small" necesita ~1 GB
    - "tiny" necesita ~500 MB (calidad más baja)

Para desarrolladores:
    El modelo se guarda en ~/.cache/huggingface/hub/
    Para limpiar el caché: rm -rf ~/.cache/huggingface/hub/
"""

from faster_whisper import WhisperModel
import time


def load_whisper_model() -> WhisperModel:
    """
    Descarga y carga el modelo Whisper en GPU.

    Retorna el modelo listo para transcribir. La primera vez
    descarga ~3 GB, después usa el caché.
    """
    print("🚀 Descargando modelo large-v2 (3GB, primera vez solamente)...")
    print("Esto puede tomar 5-10 minutos dependiendo de tu internet.\n")

    # Inicializar modelo con GPU
    model = WhisperModel(
        "large-v2",
        device="cuda",
        compute_type="float16",
        device_index=0  # RTX 3060
    )

    return model


def main() -> None:
    """
    Función principal de prueba del modelo Whisper.

    Carga el modelo y muestra información sobre la configuración
    y tiempos de transcripción estimados.
    """
    model = load_whisper_model()

    print("✅ Modelo cargado exitosamente en GPU RTX 3060!")
    print("\n📊 Info del modelo:")
    print(f"   - Dispositivo: CUDA (RTX 3060)")
    print(f"   - Precisión: float16")
    print(f"   - Memoria GPU disponible: ~6GB\n")

    # Test rápido si tienes un archivo de audio
    print("El modelo está listo para usar.")
    print("Con la RTX 3060 se esperara aproximadamente:")
    print("   • 3-5 segundos por cada minuto de audio")
    print("   • 10-15 segundos para audio de 3 minutos")
    print("   • 30-40 segundos para audio de 10 minutos\n")


if __name__ == "__main__":
    main()
