#!/usr/bin/env python3
"""
Diagnóstico de Audio - ¿Por qué V2M no escucha mi voz?

¿Cuándo usar este script?
    - V2M graba pero no transcribe nada
    - Sospechas que tu micrófono no funciona
    - Quieres encontrar el mejor micrófono disponible
    - Acabas de conectar un nuevo mic y quieres probarlo

¿Cómo funciona?
    El script te guía paso a paso:

    1. Te muestra todos los micrófonos que detecta tu computadora
    2. Te deja elegir cuál probar
    3. Te pide que hables por 3 segundos
    4. Te dice si detectó algo o no

¿Cómo lo uso?
    $ python scripts/diagnose_audio.py

    Sigue las instrucciones en pantalla. Es interactivo.

¿Qué significan los resultados?
    - Amplitud > 0.1: ¡Excelente! El mic funciona bien
    - Amplitud 0.01 - 0.1: Funciona, pero la señal es débil
    - Amplitud < 0.01: Prácticamente silencio (hay un problema)

¿Qué hago si no detecta nada?
    1. Verifica que el mic esté conectado y encendido
    2. Abre pavucontrol y revisa que el mic correcto esté seleccionado
    3. Sube el volumen del mic en alsamixer
    4. Asegúrate de que tu usuario esté en el grupo 'audio':
       $ groups | grep audio

Para desarrolladores:
    Este script usa sounddevice para captura de audio y numpy para
    calcular estadísticas de señal (amplitud máxima, media, RMS).
    El umbral de detección es 0.01, que es bastante sensible.
"""

import sounddevice as sd
import numpy as np
import sys
from typing import List, Tuple, Optional, Dict, Any


def list_audio_devices() -> List[Tuple[int, str, int]]:
    """
    Encuentra todos los micrófonos que tenés conectados.

    Escanea el sistema buscando dispositivos de audio con entrada
    y te los lista con toda la info que necesitás para config.toml.

    Returns:
        Lista de tuplas (id, nombre, sample_rate) de cada micrófono.

    Ejemplo:
        >>> devices = list_audio_devices()
        >>> for idx, name, sr in devices:
        ...     print(f"ID {idx}: {name}")
    """
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


def test_device(
    device_id: int,
    duration: int = 3,
    sample_rate: int = 16000
) -> Optional[Dict[str, Any]]:
    """
    Prueba un micrófono grabando unos segundos y midiendo el volumen.

    Graba audio del dispositivo que le pases y calcula métricas
    para saber si está funcionando o no. Te dice si detectó señal
    y qué tan fuerte fue.

    Args:
        device_id: El número del dispositivo (lo ves con list_audio_devices).
        duration: Cuántos segundos grabar. Por defecto 3.
        sample_rate: Frecuencia de muestreo. 16000 es lo estándar para Whisper.

    Returns:
        Un diccionario con los resultados:
            - device_id: El ID que probaste
            - max_amplitude: Pico más alto (0.0 a 1.0)
            - has_signal: True si detectó algo más que silencio

        Devuelve None si algo falló durante la prueba.

    Tip:
        Si max_amplitude < 0.01 es prácticamente silencio.
        Si está entre 0.01 y 0.1, funciona pero la señal es débil.
        Arriba de 0.1 es excelente.
    """
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


def main() -> None:
    """
    Corre el diagnóstico completo de audio de forma interactiva.

    Te guía paso a paso para encontrar cuál es el mejor micrófono
    para usar con V2M. El proceso es así:

        1. Lista todos los micrófonos que detecta el sistema.
        2. Te pregunta cuál querés probar (o si querés probar todos).
        3. Graba unos segundos de cada uno y mide el volumen.
        4. Te dice cuál funcionó mejor y qué poner en config.toml.

    Modos de prueba:
        - Opción 1: Solo el micrófono por defecto (la más rápida).
        - Opción 2: Probar todos uno por uno (si tenés problemas).
        - Opción 3: Probar uno específico por su número.

    Ctrl+C para cancelar en cualquier momento sin romper nada.
    """
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
