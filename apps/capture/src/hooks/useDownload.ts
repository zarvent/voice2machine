import { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, UnlistenFn } from "@tauri-apps/api/event";
import type { DownloadProgress } from "../types";

interface UseDownloadReturn {
  isDownloading: boolean;
  progress: DownloadProgress | null;
  error: string | null;
  startDownload: () => Promise<void>;
  cancelDownload: () => Promise<void>;
}

export function useDownload(): UseDownloadReturn {
  const [isDownloading, setIsDownloading] = useState(false);
  const [progress, setProgress] = useState<DownloadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let unlistenProgress: UnlistenFn | undefined;
    let unlistenComplete: UnlistenFn | undefined;

    const setupListeners = async () => {
      unlistenProgress = await listen<DownloadProgress>(
        "download-progress",
        (event) => {
          setProgress(event.payload);
          if (event.payload.status === "failed") {
            setError("Download failed");
            setIsDownloading(false);
          }
        }
      );

      unlistenComplete = await listen("download-complete", () => {
        setIsDownloading(false);
        setProgress(null);
      });
    };

    setupListeners();

    return () => {
      unlistenProgress?.();
      unlistenComplete?.();
    };
  }, []);

  const startDownload = useCallback(async () => {
    setIsDownloading(true);
    setError(null);
    setProgress({
      downloaded: 0,
      total: 0,
      percentage: 0,
      status: "preparing",
    });

    try {
      await invoke("download_model");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setIsDownloading(false);
    }
  }, []);

  const cancelDownload = useCallback(async () => {
    try {
      await invoke("cancel_download");
      setIsDownloading(false);
      setProgress(null);
    } catch (e) {
      console.error("Error canceling download:", e);
    }
  }, []);

  return {
    isDownloading,
    progress,
    error,
    startDownload,
    cancelDownload,
  };
}
