import React from 'react';

interface ConnectionIndicatorProps {
    isConnected: boolean;
}

export const ConnectionIndicator: React.FC<ConnectionIndicatorProps> = ({ isConnected }) => {
    // OPTIMIZACIÓN BOLT: Se eliminó lastPingTime para evitar re-renders cada 500ms
    return (
        <div
            title={`Estado: ${isConnected ? 'Conectado' : 'Desconectado'}`}
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
