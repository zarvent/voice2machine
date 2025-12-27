import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  BackendState,
  BackendActions,
  Status,
  TelemetryData,
  DaemonResponse,
  HistoryItem,
} from "../types";
import {
  STATUS_POLL_INTERVAL_MS,
  PING_UPDATE_INTERVAL_MS,
  HISTORY_STORAGE_KEY,
  MAX_HISTORY_ITEMS,
  SPARKLINE_HISTORY_LENGTH,
} from "../constants";

/**
 * Compara dos objetos TelemetryData campo por campo para evitar serialización JSON costosa.
 * @returns true si son idénticos, false si hay cambios.
 */
function isTelemetryEqual(
  a: TelemetryData | null,
  b: TelemetryData | null
): boolean {
  if (a === b) return true;
  if (!a || !b) return false;

  // CPU - Comparación directa de número
  if (a.cpu.percent !== b.cpu.percent) return false;

  // RAM - Comparación de campos
  if (a.ram.percent !== b.ram.percent) return false;
  if (a.ram.used_gb !== b.ram.used_gb) return false;
  if (a.ram.total_gb !== b.ram.total_gb) return false;

  // GPU - Manejo de opcionalidad
  const aGpu = a.gpu;
  const bGpu = b.gpu;
  // Si uno tiene GPU y el otro no
  if (!!aGpu !== !!bGpu) return false;
  // Si ambos tienen, comparar valores
  if (aGpu && bGpu) {
    if (aGpu.vram_used_mb !== bGpu.vram_used_mb) return false;
    if (aGpu.temp_c !== bGpu.temp_c) return false;
  }

  return true;
}

/**
 * HOOK PRINCIPAL DE COMUNICACIÓN CON BACKEND (DAEMON)
 *
 * Gestiona toda la lógica de estado, conexión IPC, manejo de errores y polling.
 * Actúa como la capa "Controlador" en el patrón MVC del frontend.
 *
 * @returns [state, actions] - Tupla con el estado actual y las acciones disponibles
 */
export function useBackend(): [BackendState, BackendActions] {
  // --- ESTADO LOCAL ---
  const [status, setStatus] = useState<Status>("disconnected");
  const [transcription, setTranscription] = useState("");
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [cpuHistory, setCpuHistory] = useState<number[]>([]);
  const [ramHistory, setRamHistory] = useState<number[]>([]);
  const [errorMessage, setErrorMessage] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [lastPingTime, setLastPingTime] = useState<number | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  // --- EFECTOS DE INICIALIZACIÓN ---

  // Cargar historial persistido al montar
  useEffect(() => {
    try {
      const saved = localStorage.getItem(HISTORY_STORAGE_KEY);
      if (saved) {
        setHistory(JSON.parse(saved));
      }
    } catch (e) {
      console.error("Failed to load history", e);
    }
  }, []);

  // --- HELPERS INTERNOS ---

  /** Guarda una nueva entrada en el historial y lo persiste */
  const addToHistory = useCallback(
    (text: string, source: "recording" | "refinement") => {
      if (!text.trim()) return;

      const newItem: HistoryItem = {
        id: crypto.randomUUID(),
        timestamp: Date.now(),
        text,
        source,
      };

      setHistory((prev) => {
        const newHistory = [newItem, ...prev].slice(0, MAX_HISTORY_ITEMS);
        localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(newHistory));
        return newHistory;
      });
    },
    []
  );

  // Refs para acceso síncrono en closures de intervalos
  const statusRef = useRef<Status>(status);
  const errorRef = useRef<string>(errorMessage);
  // OPTIMIZACIÓN BOLT: Ref para comparar telemetría sin re-renderizar
  const prevTelemetryRef = useRef<TelemetryData | null>(null);
  // OPTIMIZACIÓN BOLT: Ref para controlar la frecuencia de actualización del tiempo de ping
  const lastPingTimeRef = useRef<number>(0);

  useEffect(() => {
    statusRef.current = status;
  }, [status]);
  useEffect(() => {
    errorRef.current = errorMessage;
  }, [errorMessage]);

  /** Parsea respuesta JSON del daemon de forma segura */
  const parseResponse = useCallback((json: string): DaemonResponse => {
    try {
      return JSON.parse(json);
    } catch {
      return {};
    }
  }, []);

  // --- LÓGICA DE POLLING (Sondeo) ---

  /**
   * Consulta el estado del daemon periódicamente.
   * Es la fuente de verdad para la sincronización UI <-> Backend.
   */
  const pollStatus = useCallback(async () => {
    try {
      const response = await invoke<string>("get_status");
      setIsConnected(true);

      // OPTIMIZACIÓN BOLT: Throttling de actualización de UI para lastPingTime
      // Evita re-renderizar toda la App cada 500ms solo para actualizar un timestamp oculto en un tooltip.
      // Se actualiza solo cada 5 segundos.
      const now = Date.now();
      if (now - lastPingTimeRef.current > PING_UPDATE_INTERVAL_MS) {
        setLastPingTime(now);
        lastPingTimeRef.current = now;
      }

      const data = parseResponse(response);

      // 1. Actualizar telemetría siempre (incluso si estamos grabando)
      // OPTIMIZACIÓN BOLT: Single Pass Update & React Batching
      // Comparamos usando ref para evitar efectos secundarios en setTelemetry.
      // Las actualizaciones secuenciales se agrupan automáticamente en React 18+.
      if (data.telemetry) {
        const newTelemetry = data.telemetry;
        const prev = prevTelemetryRef.current;

        // Si la estructura cambió o es la primera vez
        if (!isTelemetryEqual(prev, newTelemetry)) {
          prevTelemetryRef.current = newTelemetry;

          setTelemetry(newTelemetry);
          setCpuHistory((h) =>
            [...h, newTelemetry.cpu.percent].slice(-SPARKLINE_HISTORY_LENGTH)
          );
          setRamHistory((h) =>
            [...h, newTelemetry.ram.percent].slice(-SPARKLINE_HISTORY_LENGTH)
          );
        }
      }

      // 2. Mapear estado interno del daemon a estados de UI
      let daemonStatus: Status = "idle";
      if (data.state === "recording") daemonStatus = "recording";
      else if (data.state === "paused") daemonStatus = "paused";
      else daemonStatus = "idle"; // Fallback por defecto

      const currentStatus = statusRef.current;

      // 3. Lógica de preservación de estado optimista "Transitional State"
      // Si la UI dice "transcribing" (procesando), no volvamos a "idle"
      // hasta que la acción termine explícitamente y actualice el estado.
      // Esto evita parpadeos en la UI.
      if (
        (currentStatus === "transcribing" || currentStatus === "processing") &&
        daemonStatus === "idle"
      ) {
        return;
      }

      // 4. Actualizar estado solo si cambió
      setStatus((prev) => {
        // Preservar estados transicionales
        if (
          (prev === "transcribing" || prev === "processing") &&
          daemonStatus === "idle"
        )
          return prev;
        // Mapeo directo
        if (daemonStatus === "recording") return "recording";
        if (daemonStatus === "paused") return "paused";

        // Recuperación tras desconexión
        if (prev === "disconnected") return daemonStatus;

        return prev !== daemonStatus ? daemonStatus : prev;
      });

      // Auto-limpiar errores al reconectar si todo está bien
      if (errorRef.current && statusRef.current === "disconnected")
        setErrorMessage("");
    } catch (e) {
      // Manejo de desconexión (daemon caído o cerrado)
      setIsConnected(false);
      setStatus("disconnected");
    }
  }, [parseResponse]);

  // Configurar intervalo de polling
  useEffect(() => {
    pollStatus(); // Fetch inicial inmediato
    const intervalId = window.setInterval(pollStatus, STATUS_POLL_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }, [pollStatus]);

  // --- ACCIONES PÚBLICAS ---

  const startRecording = useCallback(async () => {
    if (statusRef.current === "paused") return;
    try {
      await invoke("start_recording");
      setStatus("recording");
    } catch (e) {
      setErrorMessage(String(e));
      setStatus("error");
    }
  }, []);

  const stopRecording = useCallback(async () => {
    setStatus("transcribing"); // UI Optimista
    try {
      const result = await invoke<string>("stop_recording");
      const data = parseResponse(result);

      if (data.transcription) {
        setTranscription(data.transcription);
        addToHistory(data.transcription, "recording");
        setStatus("idle");
      } else {
        setErrorMessage("No se detectó voz en el audio");
        setStatus("error");
      }
    } catch (e) {
      setErrorMessage(String(e));
      setStatus("error");
    }
  }, [addToHistory, parseResponse]);

  const processText = useCallback(async () => {
    if (!transcription) return;
    setStatus("processing"); // UI Optimista
    try {
      const result = await invoke<string>("process_text", {
        text: transcription,
      });
      const data = parseResponse(result);

      if (data.refined_text) {
        setTranscription(data.refined_text);
        addToHistory(data.refined_text, "refinement");
        setStatus("idle");
      } else {
        setErrorMessage("Respuesta inesperada del LLM");
        setStatus("error");
      }
    } catch (e) {
      setErrorMessage(String(e));
      setStatus("error");
    }
  }, [transcription, addToHistory, parseResponse]);

  const togglePause = useCallback(async () => {
    try {
      if (statusRef.current === "paused") {
        await invoke("resume_daemon");
        setStatus("idle");
      } else {
        await invoke("pause_daemon");
        setStatus("paused");
      }
    } catch (e) {
      setErrorMessage(String(e));
    }
  }, []);

  const clearError = useCallback(() => setErrorMessage(""), []);

  const retryConnection = useCallback(async () => {
    await pollStatus();
  }, [pollStatus]);

  const restartDaemon = useCallback(async () => {
    setStatus("restarting");
    try {
      await invoke("restart_daemon");
      // El polling se encargará de detectar cuando vuelva a estar ONLINE
    } catch (e) {
      setErrorMessage(String(e));
      setStatus("error");
    }
  }, []);

  const shutdownDaemon = useCallback(async () => {
    setStatus("shutting_down");
    try {
      await invoke("shutdown_daemon");
      setStatus("disconnected");
      setIsConnected(false);
    } catch (e) {
      setErrorMessage(String(e));
      setStatus("error");
    }
  }, []);

  const state: BackendState = useMemo(
    () => ({
      status,
      transcription,
      telemetry,
      cpuHistory,
      ramHistory,
      errorMessage,
      isConnected,
      lastPingTime,
      history,
    }),
    [
      status,
      transcription,
      telemetry,
      cpuHistory,
      ramHistory,
      errorMessage,
      isConnected,
      lastPingTime,
      history,
    ]
  );

  const actions: BackendActions = useMemo(
    () => ({
      startRecording,
      stopRecording,
      processText,
      togglePause,
      setTranscription,
      clearError,
      retryConnection,
      restartDaemon,
      shutdownDaemon,
    }),
    [
      startRecording,
      stopRecording,
      processText,
      togglePause,
      clearError,
      retryConnection,
      restartDaemon,
      shutdownDaemon,
    ]
  );

  return [state, actions];
}
