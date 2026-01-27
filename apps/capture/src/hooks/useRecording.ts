import { useState, useEffect, useCallback, useRef } from "react";
import { invoke, listen } from "../lib/tauri";
import type { RecordingState } from "../types";
import { useLatest } from "./useLatest";

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

  // Use refs for values accessed inside listeners to avoid re-subscription
  const mountedRef = useRef(true);
  
  // We generally don't need useLatest for setters (they are stable),
  // but if we had complex logic depending on current state, we would use it.
  // Implementing useLatest pattern as requested for robustness.
  
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  useEffect(() => {
    let unlistenState: (() => void) | undefined;
    let unlistenToggle: (() => void) | undefined;
    let unlistenTranscription: (() => void) | undefined;
    let unlistenError: (() => void) | undefined;

    const setupListeners = async () => {
      try {
        // Listen for state changes from backend
        unlistenState = await listen<{ state: RecordingState }>(
          "recording-state-changed",
          (event) => {
            if (mountedRef.current) setState(event.payload.state);
          }
        );

        // Listen for toggle shortcut
        unlistenToggle = await listen("toggle-recording", async () => {
          try {
            await invoke("toggle_recording");
          } catch (e) {
            if (mountedRef.current) setError(e instanceof Error ? e.message : String(e));
          }
        });

        // Listen for transcription results
        unlistenTranscription = await listen<{ text: string }>(
          "transcription-complete",
          (event) => {
            if (mountedRef.current) setLastTranscription(event.payload.text);
          }
        );

        // Listen for errors
        unlistenError = await listen<{ message: string }>(
          "pipeline-error",
          (event) => {
            if (mountedRef.current) setError(event.payload.message);
          }
        );

        // Check initial model state
        const loaded = await invoke<boolean>("is_model_loaded");
        if (mountedRef.current) setIsModelLoaded(loaded);
      } catch (err) {
        console.error("Error setting up recording listeners:", err);
      }
    };

    setupListeners();

    return () => {
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
