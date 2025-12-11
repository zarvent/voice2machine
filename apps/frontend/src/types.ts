/**
 * Definiciones de tipos para voice2machine frontend
 * Centraliza interfaces para mantener consistencia y limpieza
 */

export type Status =
    | "idle"
    | "recording"
    | "transcribing"
    | "processing"
    | "paused"
    | "error"
    | "disconnected";

export interface TelemetryData {
    ram: {
        used_gb: number;
        total_gb: number;
        percent: number;
    };
    cpu: {
        percent: number;
    };
    gpu?: {
        vram_used_mb: number;
        temp_c: number;
    };
}

/** Estructura de respuesta cruda del daemon */
export interface DaemonResponse {
    state?: string;
    transcription?: string;
    refined_text?: string;
    message?: string;
    telemetry?: TelemetryData;
}

/** Item del historial de transcripciones */
export interface HistoryItem {
    id: string;
    timestamp: number;
    text: string;
    source: "recording" | "refinement";
}

/** Estado global del backend expuesto a la UI */
export interface BackendState {
    status: Status;
    transcription: string;
    telemetry: TelemetryData | null;
    errorMessage: string;
    isConnected: boolean;
    lastPingTime: number | null;
    history: HistoryItem[];
}

/** Acciones disponibles para la UI */
export interface BackendActions {
    startRecording: () => Promise<void>;
    stopRecording: () => Promise<void>;
    processText: () => Promise<void>;
    togglePause: () => Promise<void>;
    setTranscription: (text: string) => void;
    clearError: () => void;
    retryConnection: () => Promise<void>;
}

export interface WhisperConfig {
    model?: string;
    language?: string;
    device?: string;
    compute_type?: string;
    vad_filter?: boolean;
    beam_size?: number;
    vad_parameters?: {
        min_silence_duration_ms?: number;
        speech_pad_ms?: number;
    };
}

export interface GeminiConfig {
    api_key?: string;
    model?: string;
}

export interface LocalLLMConfig {
    model_path?: string;
    max_tokens?: number;
}

export interface LLMConfig {
    backend?: 'local' | 'gemini';
    gemini?: GeminiConfig;
    local?: LocalLLMConfig;
}

/** Configuración completa del sistema */
export interface AppConfig {
    whisper?: WhisperConfig;
    llm?: LLMConfig;
    paths?: {
        output_dir?: string;
    };
    notifications?: {
        auto_dismiss?: boolean;
        expire_time_ms?: number;
    };
    // Permitir acceso flexible para otras keys
    [key: string]: any;
}
