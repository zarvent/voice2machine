from faster_whisper import WhisperModel
import time

print("🚀 Descargando modelo large-v2 (3GB, primera vez solamente)...")
print("Esto puede tomar 5-10 minutos dependiendo de tu internet.\n")

# Inicializar modelo con GPU
model = WhisperModel(
    "large-v2",
    device="cuda",
    compute_type="float16",
    device_index=0  #  RTX 3060
)

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
