// Wrapper seguro para la API de Tauri
// Usa las funciones oficiales de @tauri-apps/api

import { invoke as tauriInvoke, isTauri as tauriIsTauri } from "@tauri-apps/api/core";
import { listen as tauriListen, type UnlistenFn } from "@tauri-apps/api/event";

// Re-exportar isTauri oficial de Tauri 2.0
export const isTauri = tauriIsTauri;

// Invoke directo (Tauri maneja internamente la disponibilidad)
export async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  return tauriInvoke<T>(cmd, args);
}

// Listen directo
export async function listen<T>(
  event: string,
  handler: (event: { payload: T }) => void
): Promise<UnlistenFn> {
  return tauriListen<T>(event, handler);
}
