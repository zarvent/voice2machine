import { useState } from "react";
import { Dashboard } from "./components/Dashboard";
import { Settings } from "./components/Settings";
import { Header } from "./components/Header";
import { MicControl } from "./components/MicControl";
import { TranscriptionArea } from "./components/TranscriptionArea";
import { useBackend } from "./hooks/useBackend";
import "./App.css";

function App() {
  const [backendState, actions] = useBackend();
  const { status, transcription, telemetry, errorMessage, isConnected, lastPingTime } = backendState;

  const [showSettings, setShowSettings] = useState(false);
  const [showDashboard, setShowDashboard] = useState(true); // Default open for control remote feel? Or closed? Let's default true but collapsible
  const [lastCopied, setLastCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(transcription);
    setLastCopied(true);
    setTimeout(() => setLastCopied(false), 2000);
  };

  return (
    <main className="app-container">
      <Header
        isConnected={isConnected}
        lastPingTime={lastPingTime}
        showDashboard={showDashboard}
        onToggleDashboard={() => setShowDashboard(!showDashboard)}
        onOpenSettings={() => setShowSettings(true)}
      />

      <div className="workspace">
        {/* Main Transcription Area */}
        <div style={{ position: 'relative', height: '100%', overflow: 'hidden' }}>

          <TranscriptionArea
            transcription={transcription}
            status={status}
            lastCopied={lastCopied}
            onTranscriptionChange={actions.setTranscription}
            onCopy={handleCopy}
            onRefine={actions.processText}
            onTogglePause={actions.togglePause}
          />

          {/* Floating Mic Control */}
          <MicControl
            status={status}
            onToggleRecord={() => {
              if (status === "recording") actions.stopRecording();
              else actions.startRecording();
            }}
          />

          {/* Error Toast (could be a proper Toast component if multiple) */}
          {status === "error" && errorMessage && (
            <div
              className="error-banner"
              role="alert"
              aria-live="assertive"
              style={{
                position: 'absolute',
                top: 20,
                left: '50%',
                transform: 'translateX(-50%)',
                width: 'auto',
                minWidth: 300
              }}
            >
              {errorMessage}
              <button
                onClick={actions.clearError}
                aria-label="Close error message"
                style={{ background: 'none', border: 'none', color: 'inherit', marginLeft: 10, cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>
          )}
        </div>

        {/* Sidebar for Dashboard (Desktop) */}
        {showDashboard && (
          <div style={{ borderLeft: '1px solid var(--border-subtle)', background: 'var(--bg-panel)', overflowY: 'auto' }}>
            <div style={{ padding: '20px', fontSize: '12px', fontWeight: 600, color: 'var(--fg-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              System Metrics
            </div>
            <Dashboard visible={true} telemetry={telemetry} />

            {/* Botón de Reinicio */}
            <div style={{ padding: '0 20px 20px' }}>
                <button
                    onClick={actions.restartDaemon}
                    disabled={status === 'restarting'}
                    className="button-secondary"
                    style={{ width: '100%' }}
                >
                    {status === 'restarting' ? 'Reiniciando...' : 'Reiniciar Daemon'}
                </button>
            </div>

            {/* Future: History List here */}
            {backendState.history && backendState.history.length > 0 && (
              <div style={{ padding: '20px', borderTop: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--fg-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>
                  History
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {backendState.history.map(item => (
                    <div
                      key={item.id}
                      role="button"
                      tabIndex={0}
                      style={{ fontSize: 13, padding: 8, background: 'var(--bg-surface)', borderRadius: 4, cursor: 'pointer' }}
                      onClick={() => actions.setTranscription(item.text)}
                      onKeyDown={(e) => e.key === 'Enter' && actions.setTranscription(item.text)}
                    >
                      <div style={{ color: 'var(--fg-secondary)', fontSize: 11 }}>{new Date(item.timestamp).toLocaleTimeString()}</div>
                      <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.text}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {showSettings && <Settings onClose={() => setShowSettings(false)} />}
    </main>
  );
}

export default App;
