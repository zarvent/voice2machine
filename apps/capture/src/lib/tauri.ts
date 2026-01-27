// Wrapper seguro para la API de Tauri
// Usa las funciones oficiales de @tauri-apps/api

import { invoke as tauriInvoke, isTauri as tauriIsTauri } from "@tauri-apps/api/core";
import { listen as tauriListen, type UnlistenFn } from "@tauri-apps/api/event";

// Re-exportar isTauri oficial de Tauri 2.0
export const isTauri = tauriIsTauri;

// Invoke directo con Mocks para modo navegador
export async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  if (!isTauri()) {
    console.warn(`[Tauri Mock] Invoke: ${cmd}`, args);
    
    // Mocks para desarrollo en navegador
    const mocks: Record<string, any> = {
      "is_model_downloaded": false,
      "is_model_loaded": false,
      "get_config": {
        audio_device_id: "default",
        language: "es",
        sound_enabled: true,
        vad: { threshold: 0.35, min_speech_duration_ms: 100, min_silence_duration_ms: 200, speech_pad_ms: 50 }
      },
      "list_audio_devices": [
        { id: "default", name: "Micrófono del Sistema (Mock)" },
        { id: "virtual", name: "CABLE Output (VB-Audio)" }
      ],
    };

    if (cmd in mocks) {
      return mocks[cmd] as T;
    }

    return Promise.resolve(undefined as unknown as T);
  }
  return tauriInvoke<T>(cmd, args);
}

// Listen directo
export async function listen<T>(
  event: string,
  handler: (event: { payload: T }) => void
): Promise<UnlistenFn> {
  if (!isTauri()) {
    console.warn(`[Tauri Mock] Listen called outside Tauri: ${event}`);
    return () => {}; // Retorna una función de limpieza vacía
  }
  return tauriListen<T>(event, handler);
}
