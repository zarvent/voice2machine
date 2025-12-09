import { useState } from "react";
import { Dashboard } from "./components/Dashboard";
import { Settings } from "./components/Settings";
import { Header } from "./components/Header";
import { MicControl } from "./components/MicControl";
import { TranscriptionArea } from "./components/TranscriptionArea";
import { useBackend } from "./hooks/useBackend";
import "./App.css";

function App() {
  const [{ status, transcription, telemetry, errorMessage }, actions] = useBackend();
  const [showSettings, setShowSettings] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [lastCopied, setLastCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(transcription);
    setLastCopied(true);
    setTimeout(() => setLastCopied(false), 2000);
  };

  return (
    <main className="app-container" role="application" aria-label="voice2machine - Transcripción de voz">
      <Header
        status={status}
        showDashboard={showDashboard}
        onToggleDashboard={() => setShowDashboard(!showDashboard)}
        onOpenSettings={() => setShowSettings(true)}
      />

      {status === "error" && errorMessage && (
        <div className="error-banner" role="alert">
          {errorMessage}
          {/* Botón clear error? maybe later */}
        </div>
      )}

      {/*
        Dashboard se mantiene montado pero oculto con CSS si se cierra
        para preservar animaciones o evitar re-renders costosos de gráficos futuros
      */}
      <div style={{ display: showDashboard ? 'block' : 'none', marginBottom: '1rem' }}>
        <Dashboard visible={true} telemetry={telemetry} />
      </div>

      {showSettings && <Settings onClose={() => setShowSettings(false)} />}

      <MicControl
        status={status}
        onToggleRecord={() => {
          if (status === "recording") actions.stopRecording();
          else actions.startRecording();
        }}
      />

      <TranscriptionArea
        transcription={transcription}
        status={status}
        lastCopied={lastCopied}
        onTranscriptionChange={actions.setTranscription}
        onCopy={handleCopy}
        onRefine={actions.processText}
        onTogglePause={actions.togglePause}
      />
    </main>
  );
}

export default App;
