
import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';

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
      alert(`Error al guardar configuración: ${error}`);
      setSaving(false);
    }
  };

  if (loading) return null; // O un spinner

  return (
    <div className="settings-overlay" style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.8)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div className="settings-modal" style={{
        background: '#1a1a1a',
        padding: '24px',
        borderRadius: '12px',
        width: '90%',
        maxWidth: '400px',
        border: '1px solid #333'
      }}>
        <h2 style={{ marginTop: 0 }}>Configuración</h2>

        <div className="form-group" style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '8px', color: '#aaa' }}>Whisper Model</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            style={{ width: '100%', padding: '8px', borderRadius: '4px', background: '#333', color: '#fff', border: 'none' }}
          >
            <option value="tiny">Tiny (Fastest)</option>
            <option value="base">Base</option>
            <option value="small">Small</option>
            <option value="medium">Medium</option>
            <option value="large-v3-turbo">Large v3 Turbo (Recommended)</option>
          </select>
        </div>

        <div className="form-group" style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', marginBottom: '8px', color: '#aaa' }}>LLM Backend</label>
          <select
            value={backend}
            onChange={(e) => setBackend(e.target.value)}
            style={{ width: '100%', padding: '8px', borderRadius: '4px', background: '#333', color: '#fff', border: 'none' }}
          >
            <option value="local">Local (Private)</option>
            <option value="gemini">Google Gemini (Cloud)</option>
          </select>
        </div>

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            style={{ padding: '8px 16px', borderRadius: '4px', border: '1px solid #444', background: 'transparent', color: '#fff', cursor: 'pointer' }}
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            style={{ padding: '8px 16px', borderRadius: '4px', border: 'none', background: '#3b82f6', color: '#fff', cursor: 'pointer', opacity: saving ? 0.7 : 1 }}
          >
            {saving ? 'Guardando...' : 'Guardar Cambios'}
          </button>
        </div>
      </div>
    </div>
  );
};
