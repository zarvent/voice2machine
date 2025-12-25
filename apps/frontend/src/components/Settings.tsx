import React, { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { AppConfig } from "../types";
import { SETTINGS_CLOSE_DELAY_MS } from "../constants";
import { Toast, ToastType } from "./Toast";

interface SettingsProps {
  onClose: () => void;
}

type TabType = "general" | "advanced";

/**
 * Modal de configuración de la aplicación.
 * Permite modificar parámetros de Whisper, selección de backend LLM y opciones avanzadas.
 */
export const Settings: React.FC<SettingsProps> = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState<TabType>("general");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState<AppConfig>({});
  // Estado local para input numérico que permite tipeo flexible
  const [maxTokensInput, setMaxTokensInput] = useState<string>("512");
  const [toast, setToast] = useState<{
    message: string;
    type: ToastType;
  } | null>(null);

  // Cargar configuración inicial desde el backend
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await invoke<string>("get_config");
        const data = JSON.parse(res);
        const loadedConfig = data.config || {};
        setConfig(loadedConfig);
        // Inicializar estado local del input
        if (loadedConfig.llm?.local?.max_tokens) {
          setMaxTokensInput(loadedConfig.llm.local.max_tokens.toString());
        }
      } catch (e) {
        console.error("Error loading config:", e);
        setToast({ message: "Error cargando configuración", type: "error" });
      } finally {
        setLoading(false);
      }
    };
    loadConfig();
  }, []);

  // Manejar cierre con tecla Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  /** Helper para actualizar estado inmutable profundo */
  const handleChange = <K extends keyof AppConfig>(
    section: K,
    key: string,
    value: unknown
  ) => {
    setConfig((prev) => ({
      ...prev,
      [section]: {
        ...(prev[section] as Record<string, unknown>),
        [key]: value,
      },
    }));
  };

  /** Guarda configuración via IPC y cierra modal */
  const handleSave = async () => {
    setSaving(true);
    try {
      await invoke("update_config", { updates: config });
      setToast({ message: "Configuración guardada", type: "success" });
      setTimeout(() => {
        setSaving(false);
        onClose();
      }, SETTINGS_CLOSE_DELAY_MS);
    } catch (error) {
      console.error("Failed to update config:", error);
      setSaving(false);
      setToast({ message: `Error al guardar: ${error}`, type: "error" });
    }
  };

  if (loading) return null;

  return (
    <div
      className="modal-overlay"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-title"
    >
      <div className="modal-content">
        <div className="modal-header">
          <div id="settings-title" className="modal-title">
            Configuración
          </div>
          <button
            onClick={onClose}
            className="btn-icon"
            aria-label="Cerrar configuración"
            autoFocus
          >
            ✕
          </button>
        </div>

        {/* TOAST NOTIFICATIONS */}
        {toast && (
          <div className="settings-toast-container">
            <Toast
              message={toast.message}
              type={toast.type}
              onDismiss={() => setToast(null)}
              duration={3000}
            />
          </div>
        )}

        {/* TABS DE NAVEGACIÓN */}
        <div className="tabs" role="tablist">
          <button
            id="tab-general"
            role="tab"
            aria-selected={activeTab === "general"}
            aria-controls="panel-general"
            className={`tab ${activeTab === "general" ? "active" : ""}`}
            onClick={() => setActiveTab("general")}
          >
            General
          </button>
          <button
            id="tab-advanced"
            role="tab"
            aria-selected={activeTab === "advanced"}
            aria-controls="panel-advanced"
            className={`tab ${activeTab === "advanced" ? "active" : ""}`}
            onClick={() => setActiveTab("advanced")}
          >
            Avanzado
          </button>
        </div>

        <div className="modal-body">
          {/* SECCIÓN GENERAL */}
          <div
            id="panel-general"
            role="tabpanel"
            aria-labelledby="tab-general"
            hidden={activeTab !== "general"}
            className={`panel-content ${
              activeTab === "general" ? "" : "panel-content--hidden"
            }`}
          >
            <div className="form-group">
              <label className="label" htmlFor="whisper-model">
                Modelo Whisper (Transcripción)
              </label>
              <select
                id="whisper-model"
                className="select"
                value={config.whisper?.model || "large-v3-turbo"}
                onChange={(e) =>
                  handleChange("whisper", "model", e.target.value)
                }
              >
                <option value="tiny">Tiny (Más rápido, menos preciso)</option>
                <option value="base">Base</option>
                <option value="small">Small</option>
                <option value="medium">Medium</option>
                <option value="large-v3-turbo">
                  Large v3 Turbo (Recomendado)
                </option>
              </select>
            </div>

            <div className="form-group">
              <label className="label" htmlFor="llm-backend">
                Backend IA (Refinamiento)
              </label>
              <select
                id="llm-backend"
                className="select"
                value={config.llm?.backend || "local"}
                onChange={(e) => handleChange("llm", "backend", e.target.value)}
              >
                <option value="local">Local (Privado - Llama/Qwen)</option>
                <option value="gemini">
                  Google Gemini (Nube - Requiere API Key)
                </option>
              </select>
            </div>

            {config.llm?.backend === "gemini" && (
              <div className="form-group">
                <label className="label" htmlFor="gemini-api-key">
                  Gemini API Key
                </label>
                <input
                  id="gemini-api-key"
                  className="input"
                  type="password"
                  placeholder="Cargada desde variable de entorno (Sólo lectura)"
                  disabled
                />
                <small className="form-hint">
                  Configure GOOGLE_API_KEY en su archivo .env
                </small>
              </div>
            )}
          </div>

          {/* SECCIÓN AVANZADA */}
          <div
            id="panel-advanced"
            role="tabpanel"
            aria-labelledby="tab-advanced"
            hidden={activeTab !== "advanced"}
            className={`panel-content ${
              activeTab === "advanced" ? "" : "panel-content--hidden"
            }`}
          >
            <div className="form-group">
              <label className="label" htmlFor="compute-type">
                Precisión de Cómputo
              </label>
              <select
                id="compute-type"
                className="select"
                value={config.whisper?.compute_type || "int8_float16"}
                onChange={(e) =>
                  handleChange("whisper", "compute_type", e.target.value)
                }
              >
                <option value="float16">float16 (Mayor consumo VRAM)</option>
                <option value="int8_float16">int8_float16 (Balanceado)</option>
                <option value="int8">int8 (Menor consumo VRAM)</option>
              </select>
            </div>

            <div className="form-group form-group--row">
              <label className="label" htmlFor="vad-filter">
                Filtro de Silencio (VAD)
              </label>
              <input
                id="vad-filter"
                type="checkbox"
                checked={config.whisper?.vad_filter ?? true}
                onChange={(e) =>
                  handleChange("whisper", "vad_filter", e.target.checked)
                }
              />
            </div>

            <div className="form-group">
              <label className="label" htmlFor="max-tokens">
                Tokens Máximos (LLM Local)
              </label>
              <input
                id="max-tokens"
                className="input"
                type="number"
                min="64"
                step="64"
                value={maxTokensInput}
                onChange={(e) => {
                  const val = e.target.value;
                  setMaxTokensInput(val);
                  const parsed = parseInt(val);
                  if (!isNaN(parsed) && parsed >= 64) {
                    handleChange("llm", "local", {
                      ...config.llm?.local,
                      max_tokens: parsed,
                    });
                  }
                }}
                onBlur={() => {
                  const parsed = parseInt(maxTokensInput);
                  if (isNaN(parsed) || parsed < 64) {
                    // Reset al último valor válido o default
                    const validVal = config.llm?.local?.max_tokens || 512;
                    setMaxTokensInput(validVal.toString());
                  } else {
                    // Formatear correctamente
                    setMaxTokensInput(parsed.toString());
                  }
                }}
              />
            </div>
          </div>
        </div>

        {/* FOOTER ACCIONES */}
        <div className="modal-footer">
          <button
            className="btn-secondary btn-cancel"
            onClick={onClose}
            disabled={saving}
          >
            Cancelar
          </button>
          <button
            className="btn-primary"
            onClick={handleSave}
            disabled={saving}
            aria-busy={saving}
          >
            {saving ? "Guardando..." : "Guardar Cambios"}
          </button>
        </div>
      </div>
    </div>
  );
};

Settings.displayName = "Settings";
