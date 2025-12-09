import { useState, useEffect, useCallback, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Dashboard } from "./components/Dashboard";
import { Settings } from "./components/Settings";
import "./App.css";

// =============================================================================
// CONSTANTES
// =============================================================================
const STATUS_POLL_INTERVAL_MS = 500;  // intervalo de polling al daemon

// =============================================================================
// TIPOS
// =============================================================================
type Status = "idle" | "recording" | "transcribing" | "processing" | "paused" | "error" | "disconnected";

// Respuesta JSON del backend Rust (ya parseada de IPCResponse)
interface DaemonData {
  state?: string;           // de GET_STATUS
  transcription?: string;   // de STOP_RECORDING
  refined_text?: string;    // de PROCESS_TEXT
  message?: string;         // de PING, START_RECORDING
  telemetry?: any;          // Telemetría del sistema
}

// =============================================================================
// SVG ICONS
// =============================================================================
const MicIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);

const StopIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" stroke="none" aria-hidden="true">
    <rect x="6" y="6" width="12" height="12" rx="2" />
  </svg>
);

const CopyIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
);

const SparklesIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
  </svg>
);

const SettingsIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"></circle>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
  </svg>
);

const PauseIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="6" y="4" width="4" height="16"></rect>
    <rect x="14" y="4" width="4" height="16"></rect>
  </svg>
);

const PlayIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="5 3 19 12 5 21 5 3"></polygon>
  </svg>
);

const ChartIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10"></line>
    <line x1="12" y1="20" x2="12" y2="4"></line>
    <line x1="6" y1="20" x2="6" y2="14"></line>
  </svg>
);

// =============================================================================
// HELPER: parsear JSON response del backend Rust
// =============================================================================
function parseBackendResponse(jsonString: string): DaemonData {
  try {
    return JSON.parse(jsonString) as DaemonData;
  } catch {
    // Si no es JSON válido, retornar objeto vacío
    return {};
  }
}

// =============================================================================
// COMPONENTE PRINCIPAL
// =============================================================================
function App() {
  const [status, setStatus] = useState<Status>("disconnected");
  const [transcription, setTranscription] = useState("");
  const [lastCopied, setLastCopied] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [telemetry, setTelemetry] = useState<any>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const pollRef = useRef<number | null>(null);

  // Polling robusto con parsing JSON
  // NOTA: 'transcribing' y 'processing' son estados optimistas de UI.
  // El daemon solo reporta 'recording' | 'idle'. Si un cliente externo
  // (hotkey, script bash) cambia el estado, habrá lag de hasta 500ms.
  const pollStatus = useCallback(async () => {
    try {
      const response = await invoke<string>("get_status");
      const data = parseBackendResponse(response);

      // Parsear estado estructurado (no basado en .includes())
      let newStatus: Status;

      if (data.state === "recording") newStatus = "recording";
      else if (data.state === "paused") newStatus = "paused";
      else newStatus = "idle";

      // Preservar estados optimistas
      if (status === "transcribing" || status === "processing") {
          // Solo si el daemon ya terminó (pasó a idle), limpiamos
          // si sigue grabando, esperamos
      } else {
          setStatus(prev => {
             // Si el frontend está en transcribing/processing, no sobreescribir con 'idle' inmediatamente
             if ((prev === "transcribing" || prev === "processing") && newStatus === "idle") {
                 // Dejar que el handler de stop maneje la transición, o timeout
                 return prev;
             }
             return prev !== newStatus ? newStatus : prev;
          });
      }

      if (data.telemetry) {
        setTelemetry(data.telemetry);
      }

      if (errorMessage) setErrorMessage(""); // Clear error on successful connection
    } catch (e) {
      setStatus("disconnected");
    }
  }, [status]); // REMOVED errorMessage from dependencies to prevent interval recreation

  useEffect(() => {
    pollStatus(); // Initial fetch
    pollRef.current = window.setInterval(pollStatus, STATUS_POLL_INTERVAL_MS);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [pollStatus]);

  const handleRecord = async () => {
    if (status === "paused") return;

    if (status === "recording") {
      setStatus("transcribing"); // Optimistic update
      try {
        const result = await invoke<string>("stop_recording");
        const data = parseBackendResponse(result);

        if (data.transcription) {
          setTranscription(data.transcription);
          setStatus("idle");
        } else {
          // Sin transcripción = error (voz no detectada)
          setErrorMessage("No se detectó voz en el audio");
          setStatus("error"); // Vuelve a error, el siguiente poll lo pondrá en idle
        }
      } catch (e) {
        // Error del backend viene como string de Rust
        setErrorMessage(String(e));
        setStatus("error");
      }
    } else {
      try {
        await invoke<string>("start_recording");
        setStatus("recording"); // Optimistic update
      } catch (e) {
        setErrorMessage(String(e));
        setStatus("error");
      }
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(transcription);
    setLastCopied(true);
    setTimeout(() => setLastCopied(false), 2000);
  };

  const handleRefine = async () => {
    if (!transcription || status !== "idle") return;
    setStatus("processing");
    try {
      const result = await invoke<string>("process_text", { text: transcription });
      const data = parseBackendResponse(result);

      if (data.refined_text) {
        setTranscription(data.refined_text);
        setStatus("idle");
      } else {
        // Fallback: usar respuesta raw si no tiene estructura esperada
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

  // Status text mapping
  const getStatusLabel = (s: Status) => {
    switch (s) {
      case "idle": return "Listo";
      case "recording": return "Grabando...";
      case "transcribing": return "Transcribiendo...";
      case "processing": return "Refinando con IA...";
      case "disconnected": return "Daemon desconectado";
      case "error": return "Error";
      case "paused": return "Pausado (Ahorro)";
    }
  };

  return (
    <main className="app-container" role="application" aria-label="voice2machine - Transcripción de voz">
      <header>
        <div className="brand">
          <MicIcon /> voice2machine
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
                onClick={() => setShowDashboard(!showDashboard)}
                className={`icon-btn ${showDashboard ? 'active' : ''}`}
                title="Métricas del Sistema"
                aria-label={showDashboard ? "Ocultar métricas del sistema" : "Mostrar métricas del sistema"}
            >
                <ChartIcon />
            </button>
            <button
                onClick={() => setShowSettings(true)}
                className="icon-btn"
                title="Configuración"
                aria-label="Abrir configuración del sistema"
            >
                <SettingsIcon />
            </button>
            <div className="status-badge" data-status={status} role="status" aria-live="polite">
              <div className="status-dot" aria-hidden="true"></div>
              {getStatusLabel(status)}
            </div>
        </div>
      </header>

      {status === "error" && errorMessage && (
        <div className="error-banner" role="alert">
          {errorMessage}
        </div>
      )}

      <Dashboard visible={showDashboard} telemetry={telemetry} />

      {showSettings && <Settings onClose={() => setShowSettings(false)} />}

      <div className="control-surface">
        <div className="mic-button-wrapper">
          {status === "recording" && (
            <>
              <div className="ripple" aria-hidden="true"></div>
              <div className="ripple" aria-hidden="true"></div>
            </>
          )}
          <button
            className={`mic-button ${status === "recording" ? "recording" : ""}`}
            onClick={handleRecord}
            disabled={status === "transcribing" || status === "processing" || status === "disconnected" || status === "paused"}
            aria-label={status === "recording" ? "Detener grabación" : "Iniciar grabación"}
          >
            {status === "recording" ? <StopIcon /> : <MicIcon />}
          </button>
        </div>
      </div>

      <div className="transcription-card">
        <textarea
          value={transcription}
          onChange={(e) => setTranscription(e.target.value)}
          placeholder={status === "paused" ? "Sistema en pausa..." : "Habla o pega texto aquí..."}
          spellCheck={false}
          aria-label="Texto transcrito"
          disabled={status === "paused"}
        />
      </div>

      <div className="action-bar">
        <button
          className="btn-secondary"
          onClick={handleCopy}
          disabled={!transcription}
          aria-label={lastCopied ? "Texto copiado" : "Copiar texto al portapapeles"}
        >
          <CopyIcon /> {lastCopied ? "¡Copiado!" : "Copiar"}
        </button>
        <button
          className="btn-secondary"
          onClick={handleRefine}
          disabled={!transcription || status !== "idle"}
          aria-label="Refinar texto con inteligencia artificial"
        >
          <SparklesIcon /> Refinar IA
        </button>
        <button
            className="btn-secondary"
            onClick={togglePause}
            disabled={status === "disconnected"}
            title={status === "paused" ? "Reanudar sistema" : "Pausar sistema para ahorrar energía"}
        >
            {status === "paused" ? <PlayIcon /> : <PauseIcon />}
             {status === "paused" ? "Reanudar" : "Pausar"}
        </button>
      </div>
    </main>
  );
}

export default App;
