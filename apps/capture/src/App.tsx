import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import SetupWizard from "./components/SetupWizard";
import SettingsPanel from "./components/SettingsPanel";
import "./App.css";

function App() {
  const [modelExists, setModelExists] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Verificar si el modelo existe al iniciar
    const checkModel = async () => {
      try {
        const exists = await invoke<boolean>("is_model_downloaded");
        setModelExists(exists);
      } catch (error) {
        console.error("Error checking model:", error);
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

  // Si el modelo no existe, mostrar el wizard de configuración
  if (!modelExists) {
    return <SetupWizard onComplete={() => setModelExists(true)} />;
  }

  // Si el modelo existe, mostrar el panel de configuración
  return <SettingsPanel />;
}

export default App;
