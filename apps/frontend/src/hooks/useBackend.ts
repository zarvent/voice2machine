import { useState, useEffect, useCallback, useRef } from 'react';
import { invoke } from '@tauri-apps/api/core';

// Tipos compartidos
export type Status = "idle" | "recording" | "transcribing" | "processing" | "paused" | "error" | "disconnected";

export interface TelemetryData {
    ram: { used_gb: number; total_gb: number; percent: number; };
    cpu: { percent: number; };
    gpu?: { vram_used_mb: number; temp_c: number; };
}

interface DaemonData {
    state?: string;
    transcription?: string;
    refined_text?: string;
    message?: string;
    telemetry?: TelemetryData;
}

interface BackendState {
    status: Status;
    transcription: string;
    telemetry: TelemetryData | null;
    errorMessage: string;
}

interface BackendActions {
    startRecording: () => Promise<void>;
    stopRecording: () => Promise<void>;
    processText: () => Promise<void>;
    togglePause: () => Promise<void>;
    setTranscription: (text: string) => void;
    clearError: () => void;
}

const STATUS_POLL_INTERVAL_MS = 500;

export function useBackend(): [BackendState, BackendActions] {
    // State
    const [status, setStatus] = useState<Status>("disconnected");
    const [transcription, setTranscription] = useState("");
    const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
    const [errorMessage, setErrorMessage] = useState("");

    const statusRef = useRef<Status>(status);
    const errorRef = useRef<string>(errorMessage);

    // Sync refs
    useEffect(() => { statusRef.current = status; }, [status]);
    useEffect(() => { errorRef.current = errorMessage; }, [errorMessage]);

    // Helper: Parse JSON safely
    const parseResponse = (json: string): DaemonData => {
        try { return JSON.parse(json); } catch { return {}; }
    };

    // Polling Logic - Stable, no dependencies that change frequently
    const pollStatus = useCallback(async () => {
        try {
            const response = await invoke<string>("get_status");
            const data = parseResponse(response);

            // Actualizar telemetría siempre
            if (data.telemetry) setTelemetry(data.telemetry);

            // Mapear estado del daemon
            let daemonStatus: Status = "idle";
            if (data.state === "recording") daemonStatus = "recording";
            else if (data.state === "paused") daemonStatus = "paused";
            else daemonStatus = "idle";

            const currentStatus = statusRef.current;

            // Lógica de preservación de estado optimista
            if ((currentStatus === "transcribing" || currentStatus === "processing") && daemonStatus === "idle") {
                return; // Esperar
            }

            // Updates
            setStatus(prev => {
                if ((prev === "transcribing" || prev === "processing") && daemonStatus === "idle") return prev;
                if (daemonStatus === "recording") return "recording";
                if (daemonStatus === "paused") return "paused";
                return prev !== daemonStatus ? daemonStatus : prev;
            });

            if (errorRef.current && statusRef.current !== "error") setErrorMessage("");

        } catch (e) {
            setStatus("disconnected");
        }
    }, []); // Empty dependency array = stable function

    useEffect(() => {
        pollStatus(); // Initial fetch
        const intervalId = window.setInterval(pollStatus, STATUS_POLL_INTERVAL_MS);
        return () => clearInterval(intervalId);
    }, [pollStatus]);

    // Actions
    const startRecording = async () => {
        if (status === "paused") return;
        try {
            await invoke("start_recording");
            setStatus("recording");
        } catch (e) {
            setErrorMessage(String(e));
            setStatus("error");
        }
    };

    const stopRecording = async () => {
        setStatus("transcribing");
        try {
            const result = await invoke<string>("stop_recording");
            const data = parseResponse(result);

            if (data.transcription) {
                setTranscription(data.transcription);
                setStatus("idle");
            } else {
                setErrorMessage("No se detectó voz en el audio");
                setStatus("error");
            }
        } catch (e) {
            setErrorMessage(String(e));
            setStatus("error");
        }
    };

    const processText = async () => {
        if (!transcription) return;
        setStatus("processing");
        try {
            const result = await invoke<string>("process_text", { text: transcription });
            const data = parseResponse(result);

            if (data.refined_text) {
                setTranscription(data.refined_text);
                setStatus("idle");
            } else {
                setErrorMessage("Respuesta inesperada del LLM");
                setStatus("error");
            }
        } catch (e) {
            setErrorMessage(String(e));
            setStatus("error");
        }
    };

    const togglePause = async () => {
        try {
            if (status === "paused") {
                await invoke("resume_daemon");
                setStatus("idle");
            } else {
                await invoke("pause_daemon");
                setStatus("paused");
            }
        } catch (e) {
            setErrorMessage(String(e));
        }
    };

    const clearError = () => setErrorMessage("");

    return [
        { status, transcription, telemetry, errorMessage },
        { startRecording, stopRecording, processText, togglePause, setTranscription, clearError }
    ];
}
