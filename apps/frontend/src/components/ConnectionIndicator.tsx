import React from 'react';

interface ConnectionIndicatorProps {
    isConnected: boolean;
    lastPingTime: number | null;
}

export const ConnectionIndicator: React.FC<ConnectionIndicatorProps> = ({ isConnected, lastPingTime }) => {
    const timeString = lastPingTime ? new Date(lastPingTime).toLocaleTimeString() : '--:--';

    return (
        <div
            title={`Estado: ${isConnected ? 'Conectado' : 'Desconectado'} (Último ping: ${timeString})`}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--fg-muted)' }}
        >
            <div
                className="connection-dot"
                data-status={isConnected ? 'connected' : 'disconnected'}
            />
            {/* Opcional: mostrar texto en desktop si hay espacio */}
        </div>
    );
};
