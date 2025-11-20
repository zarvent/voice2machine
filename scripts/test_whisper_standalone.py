import os
import sys
import numpy as np
from faster_whisper import WhisperModel
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_whisper")

def test_transcription():
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
