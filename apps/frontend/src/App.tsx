import { useState, useCallback, useEffect } from "react";
import { Dashboard } from "./components/Dashboard";
import { Settings } from "./components/Settings";
import { Header } from "./components/Header";
import { MicControl } from "./components/MicControl";
import { TranscriptionArea } from "./components/TranscriptionArea";
import { useBackend } from "./hooks/useBackend";
import { COPY_FEEDBACK_DURATION_MS } from "./constants";
import "./App.css";

/**
 * COMPONENTE RAÍZ DE LA APLICACIÓN
 * Orquesta el estado global, el layout principal y la integración de componentes.
 */
function App() {
  // Hook personalizado de lógica de negocio (Backend IPC)
  const [backendState, actions] = useBackend();
  const { status, transcription, telemetry, cpuHistory, ramHistory, errorMessage, isConnected, lastPingTime, history } = backendState;

  // Estado UI local
  const [showSettings, setShowSettings] = useState(false);
  const [showDashboard, setShowDashboard] = useState(true);
  const [lastCopied, setLastCopied] = useState(false);

  /** Maneja el copiado al portapapeles con feedback visual */
  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(transcription);
    setLastCopied(true);
    setTimeout(() => setLastCopied(false), COPY_FEEDBACK_DURATION_MS);
  }, [transcription]);

  /** Maneja doble click o enter en histórico */
  const restoreHistoryItem = useCallback((text: string) => {
    actions.setTranscription(text);
  }, [actions]);

  const handleToggleRecord = useCallback(() => {
    if (status === "recording") actions.stopRecording();
    else actions.startRecording();
  }, [status, actions]);

  // Global shortcut for toggling recording (Ctrl+Space)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.code === 'Space') {
        e.preventDefault();
        const isDisabled = status === "transcribing" || status === "processing" || status === "disconnected" || status === "paused";
        if (!isDisabled) {
          handleToggleRecord();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleToggleRecord, status]);

  const handleToggleDashboard = useCallback(() => setShowDashboard(prev => !prev), []);
  const handleOpenSettings = useCallback(() => setShowSettings(true), []);

  return (
    <main className="app-container">
      <Header
        isConnected={isConnected}
        lastPingTime={lastPingTime}
        showDashboard={showDashboard}
        onToggleDashboard={handleToggleDashboard}
        onOpenSettings={handleOpenSettings}
      />

      <div className="workspace">
        {/* --- ÁREA PRINCIPAL DE TRABAJO --- */}
        <div className="app-main-content">
          <TranscriptionArea
            transcription={transcription}
            status={status}
            lastCopied={lastCopied}
            onTranscriptionChange={actions.setTranscription}
            onCopy={handleCopy}
            onRefine={actions.processText}
            onTogglePause={actions.togglePause}
          />

          <MicControl
            status={status}
            onToggleRecord={handleToggleRecord}
          />

          {/* Notificación de error flotante */}
          {status === "error" && errorMessage && (
            <div className="error-banner error-toast-container" role="alert" aria-live="assertive">
              {errorMessage}
              <button
                onClick={actions.clearError}
                className="btn-close-error"
                aria-label="Cerrar mensaje de error"
              >
                ✕
              </button>
            </div>
          )}
        </div>

        {/* --- BARRA LATERAL (DASHBOARD) --- */}
        {showDashboard && (
          <aside className="sidebar-dashboard">
            <div className="sidebar-header">
              Métricas del Sistema
            </div>

            <Dashboard
              visible={true}
              telemetry={telemetry}
              cpuHistory={cpuHistory}
              ramHistory={ramHistory}
            />

            <div className="sidebar-section">
              <button
                onClick={actions.restartDaemon}
                disabled={status === 'restarting'}
                className="button-secondary"
                style={{ width: '100%' }} // Mantener width aquí o mover a clase btn-full
              >
                {status === 'restarting' ? 'Reiniciando...' : 'Reiniciar Daemon'}
              </button>
            </div>

            {history && history.length > 0 && (
              <div className="history-section-container">
                <div className="history-title">
                  Historial
                </div>
                <div className="history-list">
                  {history.map(item => (
                    <div
                      key={item.id}
                      role="button"
                      tabIndex={0}
                      className="history-item"
                      onClick={() => restoreHistoryItem(item.text)}
                      onKeyDown={(e) => e.key === 'Enter' && restoreHistoryItem(item.text)}
                      title="Click para restaurar"
                    >
                      <div className="history-time">
                        {new Date(item.timestamp).toLocaleTimeString()}
                      </div>
                      <div className="history-text">
                        {item.text}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </aside>
        )}
      </div>

      {showSettings && <Settings onClose={() => setShowSettings(false)} />}
    </main>
  );
}

export default App;
