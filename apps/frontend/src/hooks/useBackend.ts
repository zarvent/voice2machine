import { useState, useEffect, useCallback, useRef } from 'react';
import { invoke } from '@tauri-apps/api/core';
import {
    BackendState,
    BackendActions,
    Status,
    TelemetryData,
    DaemonResponse,
    HistoryItem
} from '../types';

const STATUS_POLL_INTERVAL_MS = 500;
const HISTORY_STORAGE_KEY = 'v2m_history_v1';
const MAX_HISTORY_ITEMS = 50;

export function useBackend(): [BackendState, BackendActions] {
    // State
    const [status, setStatus] = useState<Status>("disconnected");
    const [transcription, setTranscription] = useState("");
    const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
    const [errorMessage, setErrorMessage] = useState("");
    const [isConnected, setIsConnected] = useState(false);
    const [lastPingTime, setLastPingTime] = useState<number | null>(null);
    const [history, setHistory] = useState<HistoryItem[]>([]);

    // Load history on mount
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

    // Save history helper
    const addToHistory = (text: string, source: "recording" | "refinement") => {
        if (!text.trim()) return;

        const newItem: HistoryItem = {
            id: crypto.randomUUID(),
            timestamp: Date.now(),
            text,
            source
        };

        setHistory(prev => {
            const newHistory = [newItem, ...prev].slice(0, MAX_HISTORY_ITEMS);
            localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(newHistory));
            return newHistory;
        });
    };

    const statusRef = useRef<Status>(status);
    const errorRef = useRef<string>(errorMessage);

    // Sync refs
    useEffect(() => { statusRef.current = status; }, [status]);
    useEffect(() => { errorRef.current = errorMessage; }, [errorMessage]);

    // Helper: Parse JSON safely
    const parseResponse = (json: string): DaemonResponse => {
        try { return JSON.parse(json); } catch { return {}; }
    };

    // Polling Logic
    const pollStatus = useCallback(async () => {
        try {
            const response = await invoke<string>("get_status");
            setIsConnected(true);
            setLastPingTime(Date.now());

            const data = parseResponse(response);

            // Actualizar telemetría siempre
            if (data.telemetry) setTelemetry(data.telemetry);

            // Mapear estado del daemon
            let daemonStatus: Status = "idle";
            if (data.state === "recording") daemonStatus = "recording";
            else if (data.state === "paused") daemonStatus = "paused";
            else daemonStatus = "idle"; // Default fallback

            const currentStatus = statusRef.current;

            // Lógica de preservación de estado optimista para transiciones UI -> Backend
            if ((currentStatus === "transcribing" || currentStatus === "processing") && daemonStatus === "idle") {
                return; // Esperar a que la acción termine explícitamente y cambie el estado
            }

            // Updates state only if changed
            setStatus(prev => {
                if ((prev === "transcribing" || prev === "processing") && daemonStatus === "idle") return prev;
                if (daemonStatus === "recording") return "recording";
                if (daemonStatus === "paused") return "paused";

                // Si estábamos desconectados y volvemos, pasamos a idle (o lo que diga el daemon)
                if (prev === "disconnected") return daemonStatus;

                return prev !== daemonStatus ? daemonStatus : prev;
            });

            // Auto-clear error if connected and healthy (optional policy)
            if (errorRef.current && statusRef.current === "disconnected") setErrorMessage("");

        } catch (e) {
            setIsConnected(false);
            setStatus("disconnected");
        }
    }, []);

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
    };

    const processText = async () => {
        if (!transcription) return;
        setStatus("processing");
        try {
            const result = await invoke<string>("process_text", { text: transcription });
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

    const retryConnection = async () => {
        await pollStatus();
    };

    const state: BackendState = {
        status,
        transcription,
        telemetry,
        errorMessage,
        isConnected,
        lastPingTime,
        history
    };

    const actions: BackendActions = {
        startRecording,
        stopRecording,
        processText,
        togglePause,
        setTranscription,
        clearError,
        retryConnection
    };

    return [state, actions];
}
