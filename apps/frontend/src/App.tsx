import { useState, useEffect, useCallback, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

type Status = "idle" | "recording" | "transcribing" | "processing" | "error" | "disconnected";

function App() {
  const [status, setStatus] = useState<Status>("disconnected");
  const [transcription, setTranscription] = useState("");
  const [error, setError] = useState("");
  const pollRef = useRef<number | null>(null);

  // polling para sincronizar estado con atajos de teclado
  const pollStatus = useCallback(async () => {
    try {
      const response = await invoke<string>("get_status");
      if (response.includes("recording")) {
        setStatus("recording");
      } else if (response.includes("transcribing")) {
        setStatus("transcribing");
      } else if (response.includes("processing")) {
        setStatus("processing");
      } else {
        setStatus("idle");
      }
      setError("");
    } catch (e) {
      setStatus("disconnected");
      setError("daemon no conectado");
    }
  }, []);

  useEffect(() => {
    pollStatus();
    pollRef.current = window.setInterval(pollStatus, 500);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [pollStatus]);

  const handleRecord = async () => {
    try {
      if (status === "recording") {
        setStatus("transcribing");
        const result = await invoke<string>("stop_recording");
        if (result.startsWith("ERROR")) {
          setError(result);
        } else {
          setTranscription(result);
        }
        setStatus("idle");
      } else {
        await invoke<string>("start_recording");
        setStatus("recording");
      }
    } catch (e) {
      setError(String(e));
      setStatus("error");
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(transcription);
  };

  const handleRefine = async () => {
    if (!transcription) return;
    try {
      setStatus("processing");
      const result = await invoke<string>("process_text", { text: transcription });
      if (!result.startsWith("ERROR")) {
        setTranscription(result);
      }
      setStatus("idle");
    } catch (e) {
      setError(String(e));
      setStatus("error");
    }
  };

  const handlePing = async () => {
    try {
      const result = await invoke<string>("ping");
      setError(result === "PONG" ? "" : result);
      if (result === "PONG") setStatus("idle");
    } catch (e) {
      setError(String(e));
      setStatus("disconnected");
    }
  };

  const statusText: Record<Status, string> = {
    idle: "● Listo",
    recording: "● Grabando...",
    transcribing: "◐ Transcribiendo...",
    processing: "◐ Procesando LLM...",
    error: "● Error",
    disconnected: "○ Desconectado",
  };

  const statusColor: Record<Status, string> = {
    idle: "#22c55e",
    recording: "#ef4444",
    transcribing: "#f59e0b",
    processing: "#3b82f6",
    error: "#ef4444",
    disconnected: "#6b7280",
  };

  return (
    <main className="container">
      <h1>🎤 voice2machine</h1>

      <button
        className={`record-btn ${status === "recording" ? "recording" : ""}`}
        onClick={handleRecord}
        disabled={status === "transcribing" || status === "processing" || status === "disconnected"}
      >
        {status === "recording" ? "⏹ DETENER" : "● GRABAR"}
      </button>

      <div className="transcription-box">
        <textarea
          value={transcription}
          onChange={(e) => setTranscription(e.target.value)}
          placeholder="La transcripción aparecerá aquí..."
          rows={6}
        />
      </div>

      <div className="actions">
        <button onClick={handleCopy} disabled={!transcription}>
          📋 Copiar
        </button>
        <button onClick={handleRefine} disabled={!transcription || status !== "idle"}>
          ✨ Refinar LLM
        </button>
      </div>

      <div className="status-bar">
        <span style={{ color: statusColor[status] }}>{statusText[status]}</span>
        {status === "disconnected" && (
          <button className="retry-btn" onClick={handlePing}>
            Reintentar
          </button>
        )}
      </div>

      {error && <p className="error">{error}</p>}
    </main>
  );
}

export default App;
