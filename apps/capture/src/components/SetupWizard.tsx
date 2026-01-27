import { useEffect } from "react";
import { useDownload } from "../hooks/useDownload";
import "./SetupWizard.css";

interface SetupWizardProps {
  onComplete: () => void;
}

function SetupWizard({ onComplete }: SetupWizardProps) {
  const { isDownloading, progress, error, startDownload } = useDownload();

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const getStatusText = (): string => {
    if (!progress) return "";

    switch (progress.status) {
      case "preparing":
        return "Preparando descarga...";
      case "downloading":
        return `Descargando: ${formatBytes(progress.downloaded)} / ${formatBytes(progress.total)}`;
      case "verifying":
        return "Verificando integridad...";
      case "completed":
        return "Completado";
      case "failed":
        return "Error en la descarga";
      default:
        return "";
    }
  };

  // Detectar cuando la descarga se completa y llamar a onComplete
  useEffect(() => {
    if (progress?.status === "completed") {
      const timer = setTimeout(onComplete, 1000);
      return () => clearTimeout(timer);
    }
  }, [progress?.status, onComplete]);

  return (
    <div className="setup-wizard">
      <div className="wizard-content">
        <div className="wizard-icon">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="23" />
            <line x1="8" y1="23" x2="16" y2="23" />
          </svg>
        </div>

        <h1>Bienvenido a Capture</h1>
        <p className="wizard-description">
          Capture necesita descargar el modelo de transcripcion Whisper
          large-v3-turbo (~1.5GB) para funcionar.
        </p>

        {error && <div className="error-message" role="alert">{error}</div>}

        {isDownloading ? (
          <div className="download-progress" role="status" aria-label="Progreso de descarga">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${progress?.percentage || 0}%` }}
              />
            </div>
            <p className="progress-text">{getStatusText()}</p>
            <p className="progress-percent">
              {progress?.percentage.toFixed(1)}%
            </p>
          </div>
        ) : (
          <button
            className="download-button"
            onClick={startDownload}
            disabled={isDownloading}
          >
            Descargar Modelo
          </button>
        )}

        <div className="wizard-info">
          <h3>Caracteristicas:</h3>
          <ul>
            <li>Transcripcion local - tus grabaciones nunca salen de tu PC</li>
            <li>Soporte para Espanol e Ingles</li>
            <li>Shortcut global: Ctrl+Shift+Space</li>
            <li>Copia automatica al portapapeles</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default SetupWizard;
