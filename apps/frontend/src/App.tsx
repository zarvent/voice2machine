import {
  useState,
  useCallback,
  useEffect,
  lazy,
  Suspense,
  useMemo,
} from "react";
import { Sidebar } from "./components/Sidebar";
import { TranscriptionEditor } from "./components/TranscriptionEditor";
import { ActionBar } from "./components/ActionBar";
import { useBackend } from "./hooks/useBackend";
import { useTimer } from "./hooks/useTimer";
import { COPY_FEEDBACK_DURATION_MS } from "./constants";
import "./App.css";

const Settings = lazy(() =>
  import("./components/Settings").then((m) => ({ default: m.Settings }))
);

/** O(n) single-pass word counter - no intermediate arrays */
function countWords(text: string): number {
  let count = 0;
  let inWord = false;
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i);
    // Space, tab, newline, carriage return
    const isSpace = c === 32 || c === 9 || c === 10 || c === 13;
    if (isSpace) {
      inWord = false;
    } else if (!inWord) {
      inWord = true;
      count++;
    }
  }
  return count;
}

function App() {
  const [backendState, actions] = useBackend();
  const { status, transcription, errorMessage } = backendState;
  const timer = useTimer(status);

  const [showSettings, setShowSettings] = useState(false);
  const [lastCopied, setLastCopied] = useState(false);

  // Optimized session stats with O(n) word count
  const sessionStats = useMemo(
    () => ({
      duration: timer.formatted,
      words: countWords(transcription),
      confidence: "High",
      confidencePercent: 98,
    }),
    [transcription, timer.formatted]
  );

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(transcription);
    setLastCopied(true);
    setTimeout(() => setLastCopied(false), COPY_FEEDBACK_DURATION_MS);
  }, [transcription]);

  const handleDownload = useCallback(() => {
    const blob = new Blob([transcription], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement("a"), {
      href: url,
      download: `transcription_${new Date().toISOString().slice(0, 10)}.txt`,
    });
    a.click();
    URL.revokeObjectURL(url);
  }, [transcription]);

  // Direct refs to stable action methods (no wrapper overhead)
  const handleStartRecording = actions.startRecording;
  const handleStopRecording = actions.stopRecording;

  // Global shortcut for toggling recording (Ctrl+Space)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.code === "Space") {
        e.preventDefault();
        const isDisabled =
          status === "transcribing" ||
          status === "processing" ||
          status === "disconnected" ||
          status === "paused";
        if (!isDisabled) {
          if (status === "recording") {
            handleStopRecording();
          } else {
            handleStartRecording();
          }
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleStartRecording, handleStopRecording, status]);

  const handleOpenSettings = useCallback(() => setShowSettings(true), []);

  // Determine read-only state
  const isReadOnly = status !== "recording";

  return (
    <div className="app-layout">
      {/* Sidebar with navigation and stats */}
      <Sidebar
        sessionStats={sessionStats}
        activeNav="overview"
        onOpenSettings={handleOpenSettings}
      />

      {/* Main content area */}
      <main className="main-content">
        {/* Transcription Editor */}
        <TranscriptionEditor
          text={transcription}
          status={status}
          isReadOnly={isReadOnly}
        />

        {/* Action Bar */}
        <ActionBar
          status={status}
          transcription={transcription}
          timerFormatted={timer.formatted}
          llmProgress={status === "processing" ? 45 : null}
          onStartRecording={handleStartRecording}
          onStopRecording={handleStopRecording}
          onCopy={handleCopy}
          onDownload={handleDownload}
          copyFeedback={lastCopied}
        />

        {/* Floating error notification */}
        {status === "error" && errorMessage && (
          <div
            className="error-banner error-toast-container"
            role="alert"
            aria-live="assertive"
          >
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
      </main>

      {/* Settings Modal */}
      {showSettings && (
        <Suspense
          fallback={
            <div className="modal-overlay modal-loading">Cargando...</div>
          }
        >
          <Settings onClose={() => setShowSettings(false)} />
        </Suspense>
      )}
    </div>
  );
}

export default App;
