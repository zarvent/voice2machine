import { useState, useEffect, useCallback } from "react";
import { invoke, listen } from "../lib/tauri";
import type { RecordingState } from "../types";

interface UseRecordingReturn {
  state: RecordingState;
  isModelLoaded: boolean;
  lastTranscription: string | null;
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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let unlistenState: (() => void) | undefined;
    let unlistenToggle: (() => void) | undefined;
    let unlistenTranscription: (() => void) | undefined;
    let unlistenError: (() => void) | undefined;
    let mounted = true;

    const setupListeners = async () => {
      try {
        // Listen for state changes from backend
        unlistenState = await listen<{ state: RecordingState }>(
          "recording-state-changed",
          (event) => {
            if (mounted) setState(event.payload.state);
          }
        );

        // Listen for toggle shortcut
        unlistenToggle = await listen("toggle-recording", async () => {
          try {
            await invoke("toggle_recording");
          } catch (e) {
            if (mounted) setError(e instanceof Error ? e.message : String(e));
          }
        });

        // Listen for transcription results
        unlistenTranscription = await listen<{ text: string }>(
          "transcription-complete",
          (event) => {
            if (mounted) setLastTranscription(event.payload.text);
          }
        );

        // Listen for errors
        unlistenError = await listen<{ message: string }>(
          "pipeline-error",
          (event) => {
            if (mounted) setError(event.payload.message);
          }
        );

        // Check initial model state
        const loaded = await invoke<boolean>("is_model_loaded");
        if (mounted) setIsModelLoaded(loaded);
      } catch (err) {
        console.error("Error setting up recording listeners:", err);
      }
    };

    setupListeners();

    return () => {
      mounted = false;
      unlistenState?.();
      unlistenToggle?.();
      unlistenTranscription?.();
      unlistenError?.();
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
    error,
    toggleRecording,
    loadModel,
  };
}
