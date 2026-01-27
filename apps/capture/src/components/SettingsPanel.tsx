import { useConfig } from "../hooks/useConfig";
import { useRecording } from "../hooks/useRecording";
import type { RecordingState } from "../types";
import "./SettingsPanel.css";

const getStateColor = (state: RecordingState) => {
  switch (state) {
    case "recording":
      return "#ef4444";
    case "processing":
      return "#f59e0b";
    default:
      return "#22c55e";
  }
};

const getStateText = (state: RecordingState) => {
  switch (state) {
    case "recording":
      return "Grabando...";
    case "processing":
      return "Procesando...";
    default:
      return "Listo";
  }
};

function SettingsPanel() {
  const { config, devices, loading, updateConfig, refreshDevices } =
    useConfig();
  const { state, lastTranscription, error, toggleRecording } = useRecording();

  // Derived state for button text/state
  const isProcessing = state === "processing";
  const isIdle = state === "idle";
  const isRecording = state === "recording";

  if (loading || !config) {
    return (
      <div className="settings-panel loading">
        <div className="spinner" />
        <p>Cargando configuracion...</p>
      </div>
    );
  }

  const handleDeviceChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value || null;
    updateConfig({ audio_device_id: value });
  };

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    updateConfig({ language: e.target.value });
  };

  const handleSoundToggle = () => {
    // Functional update if possible, otherwise use current config
    updateConfig({ sound_enabled: !config.sound_enabled });
  };

  return (
    <div className="settings-panel">
      <header className="panel-header">
        <div className="logo">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="23" />
            <line x1="8" y1="23" x2="16" y2="23" />
          </svg>
        </div>
        <h1>Capture</h1>
        <div className="status-indicator" style={{ background: getStateColor(state) }}>
          {getStateText(state)}
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <section className="settings-section">
        <h2>Dispositivo de Audio</h2>
        <div className="setting-row">
          <select
            value={config.audio_device_id || ""}
            onChange={handleDeviceChange}
          >
            <option value="">Dispositivo por defecto</option>
            {devices.map((device) => (
              <option key={device.id} value={device.id}>
                {device.name} {device.is_default ? "(Default)" : ""}
              </option>
            ))}
          </select>
          <button className="icon-button" onClick={refreshDevices} title="Refrescar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 12a9 9 0 11-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
              <path d="M21 3v5h-5" />
            </svg>
          </button>
        </div>
      </section>

      <section className="settings-section">
        <h2>Idioma</h2>
        <select value={config.language} onChange={handleLanguageChange}>
          <option value="es">Espanol</option>
          <option value="en">English</option>
        </select>
      </section>

      <section className="settings-section">
        <h2>Sonidos</h2>
        <label className="toggle-setting">
          <span>Sonidos de feedback</span>
          <button
            className={`toggle-switch ${config.sound_enabled ? "active" : ""}`}
            onClick={handleSoundToggle}
          >
            <span className="toggle-thumb" />
          </button>
        </label>
      </section>

      <section className="settings-section">
        <h2>Shortcut</h2>
        <div className="shortcut-display">
          <kbd>{config.shortcut}</kbd>
        </div>
        <p className="setting-description">
          Presiona este atajo para iniciar/detener la grabacion
        </p>
      </section>

      {lastTranscription && (
        <section className="settings-section transcription-preview">
          <h2>Ultima Transcripcion</h2>
          <div className="transcription-text">{lastTranscription}</div>
        </section>
      )}

      <section className="settings-section">
        <button
          className={`record-button ${!isIdle ? "active" : ""}`}
          onClick={toggleRecording}
          disabled={isProcessing}
        >
          {isIdle
            ? "Iniciar Grabacion"
            : isRecording
              ? "Detener Grabacion"
              : "Procesando..."}
        </button>
      </section>

      <footer className="panel-footer">
        <p>
          Capture v0.1.0 - La transcripcion se realiza localmente en tu
          dispositivo
        </p>
      </footer>
    </div>
  );
}

export default SettingsPanel;
