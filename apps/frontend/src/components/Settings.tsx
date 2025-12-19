import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { AppConfig } from '../types';
import { SETTINGS_CLOSE_DELAY_MS } from '../constants';
import { Toast, ToastType } from './Toast';

interface SettingsProps {
  onClose: () => void;
}

type TabType = 'general' | 'advanced';

/**
 * Modal de configuración de la aplicación.
 * Permite modificar parámetros de Whisper, selección de backend LLM y opciones avanzadas.
 */
export const Settings: React.FC<SettingsProps> = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState<TabType>('general');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState<AppConfig>({});
  const [toast, setToast] = useState<{ message: string; type: ToastType } | null>(null);

  // Cargar configuración inicial desde el backend
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await invoke<string>('get_config');
        const data = JSON.parse(res);
        setConfig(data.config || {});
      } catch (e) {
        console.error("Error loading config:", e);
        setToast({ message: "Error cargando configuración", type: 'error' });
      } finally {
        setLoading(false);
      }
    };
    loadConfig();
  }, []);

  // Manejar cierre con tecla Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  /** Helper para actualizar estado inmutable profundo */
  const handleChange = (section: string, key: string, value: any) => {
    setConfig(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value
      }
    }));
  };

  /** Guarda configuración via IPC y cierra modal */
  const handleSave = async () => {
    setSaving(true);
    try {
      await invoke('update_config', { updates: config });
      setToast({ message: 'Configuración guardada', type: 'success' });
      setTimeout(() => {
        setSaving(false);
        onClose();
      }, SETTINGS_CLOSE_DELAY_MS);
    } catch (error) {
      console.error('Failed to update config:', error);
      setSaving(false);
      setToast({ message: `Error al guardar: ${error}`, type: 'error' });
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
      <div className="modal-content" style={{ position: 'relative' }}>
        <div className="modal-header">
          <div id="settings-title" style={{ fontWeight: 600 }}>Configuración</div>
          <button onClick={onClose} className="btn-icon" aria-label="Cerrar configuración" autoFocus>✕</button>
        </div>

        {/* TOAST NOTIFICATIONS */}
        {toast && (
          <div style={{ position: 'absolute', top: '70px', right: '20px', zIndex: 10, width: 'auto' }}>
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
            aria-selected={activeTab === 'general'}
            aria-controls="panel-general"
            className={`tab ${activeTab === 'general' ? 'active' : ''}`}
            onClick={() => setActiveTab('general')}
          >
            General
          </button>
          <button
            id="tab-advanced"
            role="tab"
            aria-selected={activeTab === 'advanced'}
            aria-controls="panel-advanced"
            className={`tab ${activeTab === 'advanced' ? 'active' : ''}`}
            onClick={() => setActiveTab('advanced')}
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
            hidden={activeTab !== 'general'}
            style={{ display: activeTab === 'general' ? 'flex' : 'none', flexDirection: 'column', gap: '20px' }}
          >
            <div className="form-group">
              <label className="label" htmlFor="whisper-model">Modelo Whisper (Transcripción)</label>
              <select
                id="whisper-model"
                className="select"
                value={config.whisper?.model || 'large-v3-turbo'}
                onChange={(e) => handleChange('whisper', 'model', e.target.value)}
              >
                <option value="tiny">Tiny (Más rápido, menos preciso)</option>
                <option value="base">Base</option>
                <option value="small">Small</option>
                <option value="medium">Medium</option>
                <option value="large-v3-turbo">Large v3 Turbo (Recomendado)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="label" htmlFor="llm-backend">Backend IA (Refinamiento)</label>
              <select
                id="llm-backend"
                className="select"
                value={config.llm?.backend || 'local'}
                onChange={(e) => handleChange('llm', 'backend', e.target.value)}
              >
                <option value="local">Local (Privado - Llama/Qwen)</option>
                <option value="gemini">Google Gemini (Nube - Requiere API Key)</option>
              </select>
            </div>

            {config.llm?.backend === 'gemini' && (
              <div className="form-group">
                <label className="label" htmlFor="gemini-api-key">Gemini API Key</label>
                <input
                  id="gemini-api-key"
                  className="input"
                  type="password"
                  placeholder="Cargada desde variable de entorno (Sólo lectura)"
                  disabled
                />
                <small style={{ color: 'var(--fg-secondary)', fontSize: '11px' }}>
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
            hidden={activeTab !== 'advanced'}
            style={{ display: activeTab === 'advanced' ? 'flex' : 'none', flexDirection: 'column', gap: '20px' }}
          >
            <div className="form-group">
              <label className="label" htmlFor="compute-type">Precisión de Cómputo</label>
              <select
                id="compute-type"
                className="select"
                value={config.whisper?.compute_type || 'int8_float16'}
                onChange={(e) => handleChange('whisper', 'compute_type', e.target.value)}
              >
                <option value="float16">float16 (Mayor consumo VRAM)</option>
                <option value="int8_float16">int8_float16 (Balanceado)</option>
                <option value="int8">int8 (Menor consumo VRAM)</option>
              </select>
            </div>

            <div className="form-group" style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
              <label className="label" htmlFor="vad-filter">Filtro de Silencio (VAD)</label>
              <input
                id="vad-filter"
                type="checkbox"
                checked={config.whisper?.vad_filter ?? true}
                onChange={(e) => handleChange('whisper', 'vad_filter', e.target.checked)}
              />
            </div>

            <div className="form-group">
              <label className="label" htmlFor="max-tokens">Tokens Máximos (LLM Local)</label>
              <input
                id="max-tokens"
                className="input"
                type="number"
                value={config.llm?.local?.max_tokens || 512}
                onChange={(e) => handleChange('llm', 'local', { ...config.llm?.local, max_tokens: parseInt(e.target.value) })}
              />
            </div>
          </div>
        </div>

        {/* FOOTER ACCIONES */}
        <div style={{ padding: '20px', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'flex-end', gap: '12px', background: 'var(--bg-panel)' }}>
          <button className="btn-secondary" onClick={onClose} disabled={saving} style={{ border: 'none' }}>Cancelar</button>
          <button
            className="btn-secondary"
            onClick={handleSave}
            disabled={saving}
            style={{ background: 'var(--fg-primary)', color: 'var(--bg-app)', borderColor: 'transparent' }}
          >
            {saving ? 'Guardando...' : 'Guardar Cambios'}
          </button>
        </div>
      </div>
    </div>
  );
};
