import { useState, useEffect, useCallback, useRef } from "react";
import { invoke, listen } from "../lib/tauri";
import type { RecordingState, PipelineEvent } from "../types";

interface UseRecordingReturn {
  state: RecordingState;
  isModelLoaded: boolean;
  lastTranscription: string | null;
  showCopiedFeedback: boolean;
  error: string | null;
  toggleRecording: () => Promise<void>;
  loadModel: () => Promise<void>;
}

export function useRecording(): UseRecordingReturn {
  const [state, setState] = useState<RecordingState>("idle");
  const [isModelLoaded, setIsModelLoaded] = useState(false);
  const [lastTranscription, setLastTranscription] = useState<string | null>(
    null
  );
  const [showCopiedFeedback, setShowCopiedFeedback] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use refs for values accessed inside listeners to avoid re-subscription
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  useEffect(() => {
    let unlistenPipeline: (() => void) | undefined;

    const setupListeners = async () => {
      try {
        // Escuchar eventos unificados del pipeline
        // El toggle ahora se maneja directamente en el backend (shortcut → toggle_recording)
        // Este listener solo actualiza el UI basado en eventos del pipeline
        unlistenPipeline = await listen<PipelineEvent>(
          "pipeline-event",
          (event) => {
            if (!mountedRef.current) return;

            const payload = event.payload;

            switch (payload.type) {
              case "state_changed":
                if (payload.state) {
                  setState(payload.state);
                }
                break;
              case "speech_started":
                // Feedback visual opcional
                break;
              case "speech_ended":
                break;
              case "transcription_complete":
                if (payload.text) {
                  setLastTranscription(payload.text);
                }
                break;
              case "copied_to_clipboard":
                setShowCopiedFeedback(true);
                setTimeout(() => {
                  if (mountedRef.current) {
                    setShowCopiedFeedback(false);
                  }
                }, 2000);
                break;
              case "error":
                if (payload.message) {
                  setError(payload.message);
                }
                break;
            }
          }
        );

        // Verificar estado inicial del modelo
        const loaded = await invoke<boolean>("is_model_loaded");
        if (mountedRef.current) setIsModelLoaded(loaded);
      } catch (err) {
        console.error("Error setting up recording listeners:", err);
      }
    };

    setupListeners();

    return () => {
      unlistenPipeline?.();
    };
  }, []);

  const toggleRecording = useCallback(async () => {
    setError(null);
    try {
      await invoke("toggle_recording");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  const loadModel = useCallback(async () => {
    try {
      await invoke("load_model");
      setIsModelLoaded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  return {
    state,
    isModelLoaded,
    lastTranscription,
    showCopiedFeedback,
    error,
    toggleRecording,
    loadModel,
  };
}
