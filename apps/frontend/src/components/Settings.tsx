
import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import styles from './Settings.module.css';

interface SettingsProps {
  onClose: () => void;
}

export const Settings: React.FC<SettingsProps> = ({ onClose }) => {
  const [model, setModel] = useState('large-v3-turbo');
  const [backend, setBackend] = useState('local');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Cargar config real al montar
    const loadConfig = async () => {
      try {
        const res = await invoke<string>('get_config');
        const data = JSON.parse(res);
        const config = data.config || {};

        if (config.whisper?.model) setModel(config.whisper.model);
        if (config.llm?.backend) setBackend(config.llm.backend);
      } catch (e) {
        console.error("Error loading config:", e);
      } finally {
        setLoading(false);
      }
    };
    loadConfig();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updates = {
        whisper: { model },
        llm: { backend }
      };

      // Enviar configuración al backend
      await invoke('update_config', { updates });

      // Simular delay para feedback visual
      setTimeout(() => {
        setSaving(false);
        onClose();
      }, 500);

    } catch (error) {
      console.error('Failed to update config:', error);
      setSaving(false);
    }
  };

  if (loading) return null; // O un spinner

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        <h2>Configuración</h2>

        <div className={styles.formGroup}>
          <label className={styles.label}>Whisper Model</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className={styles.select}
          >
            <option value="tiny">Tiny (Fastest)</option>
            <option value="base">Base</option>
            <option value="small">Small</option>
            <option value="medium">Medium</option>
            <option value="large-v3-turbo">Large v3 Turbo (Recommended)</option>
          </select>
        </div>

        <div className={styles.formGroup}>
          <label className={styles.label}>LLM Backend</label>
          <select
            value={backend}
            onChange={(e) => setBackend(e.target.value)}
            className={styles.select}
          >
            <option value="local">Local (Private)</option>
            <option value="gemini">Google Gemini (Cloud)</option>
          </select>
        </div>

        <div className={styles.buttonGroup}>
          <button
            onClick={onClose}
            className={styles.buttonCancel}
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className={styles.buttonSave}
          >
            {saving ? 'Guardando...' : 'Guardar Cambios'}
          </button>
        </div>
      </div>
    </div>
  );
};
