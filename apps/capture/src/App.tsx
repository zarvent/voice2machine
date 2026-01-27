import { useState, useEffect } from "react";
import { invoke } from "./lib/tauri";
import SetupWizard from "./components/SetupWizard";
import SettingsPanel from "./components/SettingsPanel";
import "./App.css";

function App() {
  const [modelExists, setModelExists] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkModel = async () => {
      try {
        const exists = await invoke<boolean>("is_model_downloaded");
        setModelExists(exists);
      } catch (err) {
        console.error("Error checking model:", err);
        setError(err instanceof Error ? err.message : String(err));
        setModelExists(false);
      } finally {
        setLoading(false);
      }
    };

    checkModel();
  }, []);

  if (loading) {
    return (
      <div className="app loading">
        <div className="spinner" />
        <p>Cargando...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app error">
        <p>Error: {error}</p>
        <button onClick={() => window.location.reload()}>Reintentar</button>
      </div>
    );
  }

  // Si el modelo no existe, mostrar el wizard de configuracion
  if (!modelExists) {
    return <SetupWizard onComplete={() => setModelExists(true)} />;
  }

  // Si el modelo existe, mostrar el panel de configuracion
  return <SettingsPanel />;
}

export default App;
