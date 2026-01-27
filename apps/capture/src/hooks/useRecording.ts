import { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, UnlistenFn } from "@tauri-apps/api/event";
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
    let unlistenState: UnlistenFn | undefined;
    let unlistenToggle: UnlistenFn | undefined;
    let unlistenTranscription: UnlistenFn | undefined;
    let unlistenError: UnlistenFn | undefined;

    const setupListeners = async () => {
      // Listen for state changes from backend
      unlistenState = await listen<{ state: RecordingState }>(
        "recording-state-changed",
        (event) => {
          setState(event.payload.state);
        }
      );

      // Listen for toggle shortcut
      unlistenToggle = await listen("toggle-recording", async () => {
        try {
          await invoke("toggle_recording");
        } catch (e) {
          setError(e instanceof Error ? e.message : String(e));
        }
      });

      // Listen for transcription results
      unlistenTranscription = await listen<{ text: string }>(
        "transcription-complete",
        (event) => {
          setLastTranscription(event.payload.text);
        }
      );

      // Listen for errors
      unlistenError = await listen<{ message: string }>(
        "pipeline-error",
        (event) => {
          setError(event.payload.message);
        }
      );
    };

    setupListeners();

    // Check initial model state
    invoke<boolean>("is_model_loaded")
      .then(setIsModelLoaded)
      .catch(console.error);

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
