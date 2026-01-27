// Types for Tauri IPC communication

export type RecordingState = "idle" | "recording" | "processing";

export type DownloadStatus =
  | "preparing"
  | "downloading"
  | "verifying"
  | "completed"
  | "failed";

export interface DownloadProgress {
  downloaded: number;
  total: number;
  percentage: number;
  status: DownloadStatus;
}

export interface AppConfig {
  audio_device_id: string | null;
  shortcut: string;
  language: string;
  sound_enabled: boolean;
  vad: VadConfig;
}

export interface VadConfig {
  threshold: number;
  min_speech_duration_ms: number;
  min_silence_duration_ms: number;
  speech_pad_ms: number;
  energy_fallback_threshold: number;
}

export interface AudioDeviceInfo {
  id: string;
  name: string;
  is_default: boolean;
}

export interface ModelInfo {
  path: string;
  name: string;
  size_bytes: number;
  verified: boolean;
}

export interface PipelineEvent {
  type:
    | "state_changed"
    | "speech_started"
    | "speech_ended"
    | "transcription_complete"
    | "copied_to_clipboard"
    | "error";
  data?: unknown;
}
