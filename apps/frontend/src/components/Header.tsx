import React from 'react';
import { ChartIcon, SettingsIcon, MicIcon, GithubIcon } from "../assets/Icons";
import { Status } from "../hooks/useBackend";

interface HeaderProps {
    status: Status;
    showDashboard: boolean;
    onToggleDashboard: () => void;
    onOpenSettings: () => void;
}

export const Header = React.memo(({ status, showDashboard, onToggleDashboard, onOpenSettings }: HeaderProps) => {
    const getStatusLabel = (s: Status) => {
        switch (s) {
            case "idle": return "Listo";
            case "recording": return "Grabando...";
            case "transcribing": return "Transcribiendo...";
            case "processing": return "Refinando con IA...";
            case "disconnected": return "Daemon desconectado";
            case "error": return "Error";
            case "paused": return "Pausado (Ahorro)";
        }
    };

    return (
        <header>
            <div className="brand">
                <MicIcon /> voice2machine
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <button
                    onClick={onToggleDashboard}
                    className={`icon-btn ${showDashboard ? 'active' : ''}`}
                    title="Métricas del Sistema"
                >
                    <ChartIcon />
                </button>
                <a
                    href="https://github.com/zarvent/voice2machine"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="icon-btn github-link"
                    title="Ver en GitHub"
                >
                    <GithubIcon />
                </a>
                <button
                    onClick={onOpenSettings}
                    className="icon-btn"
                    title="Configuración"
                >
                    <SettingsIcon />
                </button>
                <div className="status-badge" data-status={status} role="status" aria-live="polite">
                    <div className="status-dot" aria-hidden="true"></div>
                    {getStatusLabel(status)}
                </div>
            </div>
        </header>
    );
});
