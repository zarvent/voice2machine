import React from 'react';
import { ChartIcon, SettingsIcon, GithubIcon } from "../assets/Icons";
import { ConnectionIndicator } from "./ConnectionIndicator";

interface HeaderProps {
    isConnected: boolean;
    lastPingTime: number | null;
    showDashboard: boolean;
    onToggleDashboard: () => void;
    onOpenSettings: () => void;
}

export const Header = React.memo(({
    isConnected,
    lastPingTime,
    showDashboard,
    onToggleDashboard,
    onOpenSettings
}: HeaderProps) => {
    return (
        <header>
            <div className="brand">
                <div style={{ width: 16, height: 16, background: 'var(--fg-primary)', borderRadius: 4 }}></div>
                voice2machine
            </div>

            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <ConnectionIndicator isConnected={isConnected} lastPingTime={lastPingTime} />

                <div style={{ width: 1, height: 24, background: 'var(--border-subtle)', margin: '0 8px' }}></div>

                <a
                    href="https://github.com/zarvent/voice2machine"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-icon"
                    title="Code on GitHub"
                >
                    <GithubIcon />
                </a>

                <button
                    onClick={onToggleDashboard}
                    className={`btn-icon ${showDashboard ? 'active' : ''}`}
                    title="System Metrics"
                >
                    <ChartIcon />
                </button>

                <button
                    onClick={onOpenSettings}
                    className="btn-icon"
                    title="Settings"
                >
                    <SettingsIcon />
                </button>
            </div>
        </header>
    );
});
