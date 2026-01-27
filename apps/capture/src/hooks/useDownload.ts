import { useState, useEffect, useCallback } from "react";
import { invoke, listen } from "../lib/tauri";
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
    let unlistenProgress: (() => void) | undefined;
    let unlistenComplete: (() => void) | undefined;
    let mounted = true;

    const setupListeners = async () => {
      try {
        unlistenProgress = await listen<DownloadProgress>(
          "download-progress",
          (event) => {
            if (!mounted) return;
            setProgress(event.payload);
            if (event.payload.status === "failed") {
              setError("Download failed");
              setIsDownloading(false);
            }
          }
        );

        unlistenComplete = await listen("download-complete", () => {
          if (!mounted) return;
          setIsDownloading(false);
          // Mantener el estado de progreso con status completado
          setProgress((prev) =>
            prev
              ? { ...prev, status: "completed", percentage: 100 }
              : {
                  downloaded: 0,
                  total: 0,
                  percentage: 100,
                  status: "completed",
                }
          );
        });
      } catch (err) {
        console.error("Error setting up listeners:", err);
      }
    };

    setupListeners();

    return () => {
      mounted = false;
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
