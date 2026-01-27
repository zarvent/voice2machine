import { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import type { AppConfig, AudioDeviceInfo } from "../types";

interface UseConfigReturn {
  config: AppConfig | null;
  devices: AudioDeviceInfo[];
  loading: boolean;
  error: string | null;
  updateConfig: (newConfig: Partial<AppConfig>) => Promise<void>;
  refreshDevices: () => Promise<void>;
}

const DEFAULT_CONFIG: AppConfig = {
  audio_device_id: null,
  shortcut: "Ctrl+Shift+Space",
  language: "es",
  sound_enabled: true,
  vad: {
    threshold: 0.35,
    min_speech_duration_ms: 150,
    min_silence_duration_ms: 800,
    speech_pad_ms: 300,
    energy_fallback_threshold: 0.005,
  },
};

export function useConfig(): UseConfigReturn {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [devices, setDevices] = useState<AudioDeviceInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConfig = useCallback(async () => {
    try {
      const cfg = await invoke<AppConfig>("get_config");
      setConfig(cfg);
    } catch (e) {
      console.error("Error fetching config:", e);
      setConfig(DEFAULT_CONFIG);
    }
  }, []);

  const refreshDevices = useCallback(async () => {
    try {
      const deviceList = await invoke<AudioDeviceInfo[]>("list_audio_devices");
      setDevices(deviceList);
    } catch (e) {
      console.error("Error fetching devices:", e);
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([fetchConfig(), refreshDevices()]);
      setLoading(false);
    };

    init();
  }, [fetchConfig, refreshDevices]);

  const updateConfig = useCallback(
    async (newConfig: Partial<AppConfig>) => {
      if (!config) return;

      const updated = { ...config, ...newConfig };

      try {
        await invoke("set_config", { newConfig: updated });
        setConfig(updated);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        throw e;
      }
    },
    [config]
  );

  return {
    config,
    devices,
    loading,
    error,
    updateConfig,
    refreshDevices,
  };
}
