#!/usr/bin/env python3
"""
Diagnóstico de Audio - Voice2Machine (V2M)
Prueba todos los dispositivos de entrada y muestra amplitudes en tiempo real.
"""

import sounddevice as sd
import numpy as np
import sys
from typing import List, Tuple


def list_audio_devices() -> List[Tuple[int, str, int]]:
    """Lista todos los dispositivos de entrada disponibles."""
    devices = sd.query_devices()
    input_devices = []

    print("=" * 70)
    print(" DISPOSITIVOS DE AUDIO DISPONIBLES")
    print("=" * 70)

    for idx, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"[{idx}] {device['name']}")
            print(f"    Canales: {device['max_input_channels']}")
            print(f"    Sample Rate: {device['default_samplerate']} Hz")
            print()
            input_devices.append((
                idx,
                device['name'],
                int(device['default_samplerate'])
            ))

    return input_devices


def test_device(device_id: int, duration: int = 3, sample_rate: int = 16000):
    """Prueba un dispositivo específico y muestra estadísticas de amplitud."""
    print("=" * 70)
    print(f" PROBANDO DISPOSITIVO {device_id}")
    print("=" * 70)
    print(f"Duración: {duration} segundos")
    print(f"Sample Rate: {sample_rate} Hz")
    print("\n🎤 HABLA AHORA (fuerte y claro)...\n")

    try:
        # Grabar audio
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype=np.float32,
            device=device_id
        )
        sd.wait()  # Esperar a que termine la grabación

        # Calcular estadísticas
        audio_data = recording.flatten()
        max_amplitude = np.max(np.abs(audio_data))
        mean_amplitude = np.mean(np.abs(audio_data))
        rms = np.sqrt(np.mean(audio_data**2))

        # Determinar si hay señal útil
        threshold = 0.01
        has_signal = max_amplitude > threshold

        print("=" * 70)
        print(" RESULTADOS")
        print("=" * 70)
        print(f"Amplitud Máxima:  {max_amplitude:.6f}")
        print(f"Amplitud Media:   {mean_amplitude:.6f}")
        print(f"RMS:              {rms:.6f}")
        print(f"Muestras:         {len(audio_data)}")
        print()

        if has_signal:
            print("✅ SEÑAL DETECTADA - Este dispositivo parece funcionar")
            if max_amplitude < 0.1:
                print("⚠️  Advertencia: Señal muy débil. Considera aumentar el volumen del micrófono.")
        else:
            print("❌ SIN SEÑAL - Silencio digital o dispositivo inactivo")

        print("=" * 70)

        return {
            'device_id': device_id,
            'max_amplitude': max_amplitude,
            'mean_amplitude': mean_amplitude,
            'rms': rms,
            'has_signal': has_signal
        }

    except Exception as e:
        print(f"❌ ERROR al probar dispositivo {device_id}: {e}")
        return None


def main():
    """Función principal del diagnóstico."""
    print("\n🔍 INICIANDO DIAGNÓSTICO DE AUDIO\n")

    # Listar dispositivos
    input_devices = list_audio_devices()

    if not input_devices:
        print("❌ No se encontraron dispositivos de entrada")
        sys.exit(1)

    # Probar dispositivo por defecto
    default_device = sd.query_devices(kind='input')
    print(f"\n🎯 Dispositivo por defecto del sistema: {default_device['name']}\n")

    # Preguntar qué dispositivo probar
    print("\nOpciones:")
    print("  1. Probar SOLO el dispositivo por defecto")
    print("  2. Probar TODOS los dispositivos (recomendado si hay problemas)")
    print("  3. Probar un dispositivo específico")

    try:
        choice = input("\nSelecciona una opción (1/2/3) [default=1]: ").strip() or "1"

        results = []

        if choice == "1":
            # Probar solo el dispositivo por defecto
            default_id = sd.query_devices(kind='input')['index']
            result = test_device(default_id)
            if result:
                results.append(result)

        elif choice == "2":
            # Probar todos los dispositivos
            for device_id, device_name, sample_rate in input_devices:
                print(f"\n📍 Siguiente: {device_name}")
                input("Presiona ENTER para continuar...")
                result = test_device(device_id, duration=3, sample_rate=sample_rate)
                if result:
                    results.append(result)

        elif choice == "3":
            # Probar un dispositivo específico
            device_id = int(input("\nIngresa el ID del dispositivo a probar: "))
            sample_rate = 16000  # Usar el estándar de Whisper
            result = test_device(device_id, duration=3, sample_rate=sample_rate)
            if result:
                results.append(result)
        else:
            print("Opción inválida")
            sys.exit(1)

        # Resumen final
        if results:
            print("\n" + "=" * 70)
            print(" RESUMEN FINAL")
            print("=" * 70)

            working_devices = [r for r in results if r['has_signal']]

            if working_devices:
                print(f"\n✅ {len(working_devices)} dispositivo(s) con señal detectada:\n")
                for r in sorted(working_devices, key=lambda x: x['max_amplitude'], reverse=True):
                    device_name = sd.query_devices(r['device_id'])['name']
                    print(f"  ID {r['device_id']}: {device_name}")
                    print(f"    → Amplitud Máxima: {r['max_amplitude']:.6f}")
                    print()

                best_device = working_devices[0]
                print(f"🎯 RECOMENDACIÓN: Usar device_index = {best_device['device_id']}")
                print(f"\nActualiza config.toml con:")
                print(f"  device_index = {best_device['device_id']}")
                print(f"  vad_filter = false  # Para testing inicial")
            else:
                print("\n❌ Ningún dispositivo mostró señal de audio.")
                print("\nPosibles causas:")
                print("  - Micrófono desconectado o apagado")
                print("  - Micrófono silenciado en el sistema")
                print("  - Permisos insuficientes")
                print("\nVerifica:")
                print("  1. pavucontrol (para configuración de PulseAudio)")
                print("  2. alsamixer (para niveles de volumen)")
                print("  3. Permisos del usuario en el grupo 'audio'")

            print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n⚠️  Diagnóstico interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
