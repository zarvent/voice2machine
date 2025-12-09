import { useState, useEffect, useCallback, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

// SVG Icons as components for cleaner JSX
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

type Status = "idle" | "recording" | "transcribing" | "processing" | "error" | "disconnected";

function App() {
  const [status, setStatus] = useState<Status>("disconnected");
  const [transcription, setTranscription] = useState("");
  const [lastCopied, setLastCopied] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const pollRef = useRef<number | null>(null);

  // Optimized polling
  const pollStatus = useCallback(async () => {
    try {
      const response = await invoke<string>("get_status");
      // Map daemon response strings to our app state
      const newStatus: Status =
        response.includes("recording") ? "recording" :
          response.includes("transcribing") ? "transcribing" :
            response.includes("processing") ? "processing" :
              "idle";

      setStatus(prev => prev !== newStatus ? newStatus : prev);
      if (errorMessage) setErrorMessage(""); // Clear error on successful connection
    } catch (e) {
      setStatus("disconnected");
    }
  }, [errorMessage]);

  useEffect(() => {
    pollStatus(); // Initial fetch
    pollRef.current = window.setInterval(pollStatus, 500);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [pollStatus]);

  const handleRecord = async () => {
    if (status === "recording") {
      setStatus("transcribing"); // Optimistic update
      try {
        const result = await invoke<string>("stop_recording");
        if (result.startsWith("ERROR")) {
          setErrorMessage(result);
          setStatus("error");
        } else {
          setTranscription(result);
        }
      } catch (e) {
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
      if (result.startsWith("ERROR")) {
        setErrorMessage(result);
        setStatus("error");
      } else {
        setTranscription(result);
        setStatus("idle");
      }
    } catch (e) {
      setErrorMessage(String(e));
      setStatus("error");
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
    }
  };

  return (
    <main className="app-container" role="application" aria-label="voice2machine - Transcripción de voz">
      <header>
        <div className="brand">
          <MicIcon /> voice2machine
        </div>
        <div className="status-badge" data-status={status} role="status" aria-live="polite">
          <div className="status-dot" aria-hidden="true"></div>
          {getStatusLabel(status)}
        </div>
      </header>

      {status === "error" && errorMessage && (
        <div className="error-banner" role="alert">
          {errorMessage}
        </div>
      )}

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
            disabled={status === "transcribing" || status === "processing" || status === "disconnected"}
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
          placeholder="Habla o pega texto aquí..."
          spellCheck={false}
          aria-label="Texto transcrito"
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
      </div>
    </main>
  );
}

export default App;
