import { useState, useCallback, useEffect, lazy, Suspense } from "react";
import { Header } from "./components/Header";
import { MicControl } from "./components/MicControl";
import { Studio } from "./components/Studio";
import { DaemonControls } from "./components/DaemonControls";
import { useBackend } from "./hooks/useBackend";
import { useNotes } from "./hooks/useNotes";
import "./App.css";

// Lazy loading para componentes pesados (code splitting)
const Dashboard = lazy(() =>
  import("./components/Dashboard").then((m) => ({ default: m.Dashboard }))
);
const Settings = lazy(() =>
  import("./components/Settings").then((m) => ({ default: m.Settings }))
);

/**
 * COMPONENTE RAÍZ DE LA APLICACIÓN
 * Orquesta el estado global, el layout principal y la integración de componentes.
 */
function App() {
  // Hook de comunicación con Backend (daemon Python)
  const [backendState, backendActions] = useBackend();
  const {
    status,
    telemetry,
    cpuHistory,
    ramHistory,
    errorMessage,
    isConnected,
    lastPingTime,
    history,
  } = backendState;

  // Hook de gestión de notas del Studio
  const [notesState, notesActions] = useNotes();

  // Estado UI local
  const [showSettings, setShowSettings] = useState(false);
  const [showDashboard, setShowDashboard] = useState(true);

  // Sincronizar transcripción del backend con la nota activa
  useEffect(() => {
    const activeNote = notesActions.getActiveNote();
    if (backendState.transcription && activeNote) {
      // Solo actualizar si hay nueva transcripción del backend
      if (backendState.transcription !== activeNote.content) {
        notesActions.updateActiveNoteContent(backendState.transcription);
      }
    }
  }, [backendState.transcription, notesActions]);

  /** Maneja el proceso de refinar con IA (usa contenido de nota activa) */
  const handleRefine = useCallback(async () => {
    const activeNote = notesActions.getActiveNote();
    if (activeNote?.content) {
      // Sincronizar el contenido de la nota activa al backend antes de procesar
      backendActions.setTranscription(activeNote.content);
      await backendActions.processText();
    }
  }, [notesActions, backendActions]);

  /** Maneja doble click o enter en histórico */
  const restoreHistoryItem = useCallback(
    (text: string) => {
      notesActions.updateActiveNoteContent(text);
    },
    [notesActions]
  );

  const handleToggleRecord = useCallback(() => {
    if (status === "recording") backendActions.stopRecording();
    else backendActions.startRecording();
  }, [status, backendActions]);

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isCtrlOrMeta = e.ctrlKey || e.metaKey;

      // Ctrl+Space - Toggle recording
      if (isCtrlOrMeta && e.code === "Space") {
        e.preventDefault();
        const isDisabled =
          status === "transcribing" ||
          status === "processing" ||
          status === "disconnected" ||
          status === "paused";
        if (!isDisabled) {
          handleToggleRecord();
        }
        return;
      }

      // Ctrl+T - New note
      if (isCtrlOrMeta && e.key.toLowerCase() === "t") {
        e.preventDefault();
        notesActions.createNote();
        return;
      }

      // Ctrl+W - Close current note
      if (isCtrlOrMeta && e.key.toLowerCase() === "w") {
        e.preventDefault();
        const activeNote = notesActions.getActiveNote();
        if (activeNote && notesState.notes.length > 1) {
          notesActions.deleteNote(activeNote.id);
        }
        return;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleToggleRecord, status, notesActions, notesState.notes.length]);

  const handleToggleDashboard = useCallback(
    () => setShowDashboard((prev) => !prev),
    []
  );
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
        {/* --- ÁREA PRINCIPAL DE TRABAJO (STUDIO) --- */}
        <div className="app-main-content">
          <Studio
            notesState={notesState}
            notesActions={notesActions}
            status={status}
            onRefine={handleRefine}
            onTogglePause={backendActions.togglePause}
          />

          <MicControl status={status} onToggleRecord={handleToggleRecord} />

          {/* Notificación de error flotante */}
          {status === "error" && errorMessage && (
            <div
              className="error-banner error-toast-container"
              role="alert"
              aria-live="assertive"
            >
              {errorMessage}
              <button
                onClick={backendActions.clearError}
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
            <div className="sidebar-header">Métricas del Sistema</div>

            <Suspense
              fallback={<div className="sidebar-loading">Cargando...</div>}
            >
              <Dashboard
                visible={true}
                telemetry={telemetry}
                cpuHistory={cpuHistory}
                ramHistory={ramHistory}
              />
            </Suspense>

            <DaemonControls
              status={status}
              onRestart={backendActions.restartDaemon}
              onShutdown={backendActions.shutdownDaemon}
            />

            {history && history.length > 0 && (
              <div className="history-section-container">
                <div className="history-title">Historial</div>
                <div className="history-list">
                  {history.map((item) => (
                    <div
                      key={item.id}
                      role="button"
                      tabIndex={0}
                      className="history-item"
                      onClick={() => restoreHistoryItem(item.text)}
                      onKeyDown={(e) =>
                        e.key === "Enter" && restoreHistoryItem(item.text)
                      }
                      title="Click para restaurar"
                    >
                      <div className="history-time">
                        {new Date(item.timestamp).toLocaleTimeString()}
                      </div>
                      <div className="history-text">{item.text}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </aside>
        )}
      </div>

      {showSettings && (
        <Suspense
          fallback={
            <div className="modal-overlay modal-loading">Cargando...</div>
          }
        >
          <Settings onClose={() => setShowSettings(false)} />
        </Suspense>
      )}
    </main>
  );
}

export default App;
