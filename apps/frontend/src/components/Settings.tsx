import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { AppConfig } from '../types';

interface SettingsProps {
  onClose: () => void;
}

type TabType = 'general' | 'advanced';

export const Settings: React.FC<SettingsProps> = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState<TabType>('general');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState<AppConfig>({});

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await invoke<string>('get_config');
        const data = JSON.parse(res);
        setConfig(data.config || {});
      } catch (e) {
        console.error("Error loading config:", e);
      } finally {
        setLoading(false);
      }
    };
    loadConfig();
  }, []);

  const handleChange = (section: string, key: string, value: any) => {
    setConfig(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value
      }
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Send only what changed ideally, but sending connection is ok
      await invoke('update_config', { updates: config });
      setTimeout(() => {
        setSaving(false);
        onClose();
      }, 500);
    } catch (error) {
      console.error('Failed to update config:', error);
      setSaving(false);
    }
  };

  if (loading) return null;

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-content">
        <div className="modal-header">
          <div style={{ fontWeight: 600 }}>Settings</div>
          <button onClick={onClose} className="btn-icon">✕</button>
        </div>

        <div className="tabs" role="tablist">
          <button
            role="tab"
            aria-selected={activeTab === 'general'}
            className={`tab ${activeTab === 'general' ? 'active' : ''}`}
            onClick={() => setActiveTab('general')}
          >
            General
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'advanced'}
            className={`tab ${activeTab === 'advanced' ? 'active' : ''}`}
            onClick={() => setActiveTab('advanced')}
          >
            Advanced
          </button>
        </div>

        <div className="modal-body">
          {activeTab === 'general' && (
            <>
              <div className="form-group">
                <label className="label">Whisper Model</label>
                <select
                  className="select"
                  value={config.whisper?.model || 'large-v3-turbo'}
                  onChange={(e) => handleChange('whisper', 'model', e.target.value)}
                >
                  <option value="tiny">Tiny (Fastest)</option>
                  <option value="base">Base</option>
                  <option value="small">Small</option>
                  <option value="medium">Medium</option>
                  <option value="large-v3-turbo">Large v3 Turbo (Recommended)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="label">LLM Backend</label>
                <select
                  className="select"
                  value={config.llm?.backend || 'local'}
                  onChange={(e) => handleChange('llm', 'backend', e.target.value)}
                >
                  <option value="local">Local (Private - Qwen/Llama)</option>
                  <option value="gemini">Google Gemini (Cloud)</option>
                </select>
              </div>

              {config.llm?.backend === 'gemini' && (
                <div className="form-group">
                  <label className="label">Gemini API Key</label>
                  <input
                    className="input"
                    type="password"
                    placeholder="Loaded from Env (Read-only)"
                    disabled
                  />
                </div>
              )}
            </>
          )}

          {activeTab === 'advanced' && (
            <>
              <div className="form-group">
                <label className="label">Compute Type</label>
                <select
                  className="select"
                  value={config.whisper?.compute_type || 'int8_float16'}
                  onChange={(e) => handleChange('whisper', 'compute_type', e.target.value)}
                >
                  <option value="float16">float16 (Best VRAM)</option>
                  <option value="int8_float16">int8_float16 (Balanced)</option>
                  <option value="int8">int8 (Lowest VRAM)</option>
                </select>
              </div>

              <div className="form-group" style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                <label className="label">VAD Filtering (Voice Activity Detection)</label>
                <input
                  type="checkbox"
                  checked={config.whisper?.vad_filter ?? true}
                  onChange={(e) => handleChange('whisper', 'vad_filter', e.target.checked)}
                />
              </div>

              <div className="form-group">
                <label className="label">LLM Max Tokens</label>
                <input
                  className="input"
                  type="number"
                  value={config.llm?.local?.max_tokens || 512}
                  onChange={(e) => handleChange('llm', 'local', { ...config.llm?.local, max_tokens: parseInt(e.target.value) })}
                />
              </div>
            </>
          )}
        </div>

        <div style={{ padding: '20px', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'flex-end', gap: '12px', background: 'var(--bg-panel)' }}>
          <button className="btn-secondary" onClick={onClose} disabled={saving} style={{ border: 'none' }}>Cancel</button>
          <button
            className="btn-secondary"
            onClick={handleSave}
            disabled={saving}
            style={{ background: 'var(--fg-primary)', color: 'var(--bg-app)', borderColor: 'transparent' }}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};
