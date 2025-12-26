import React from "react";

interface ConnectionIndicatorProps {
  isConnected: boolean;
  lastPingTime: number | null;
}

export const ConnectionIndicator: React.FC<ConnectionIndicatorProps> = ({
  isConnected,
  lastPingTime,
}) => {
  const timeString = lastPingTime
    ? new Date(lastPingTime).toLocaleTimeString()
    : "--:--";

  const statusLabel = isConnected ? "Sistema conectado" : "Sistema desconectado";
  const tooltip = `Estado: ${isConnected ? "Conectado" : "Desconectado"} (Último ping: ${timeString})`;

  return (
    <div
      role="status"
      aria-label={statusLabel}
      tabIndex={0}
      title={tooltip}
      className="connection-indicator"
    >
      <div
        className="connection-dot"
        data-status={isConnected ? "connected" : "disconnected"}
      />
    </div>
  );
};

ConnectionIndicator.displayName = "ConnectionIndicator";
