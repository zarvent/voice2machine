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

  return (
    <div
      title={`Estado: ${
        isConnected ? "Conectado" : "Desconectado"
      } (Último ping: ${timeString})`}
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
