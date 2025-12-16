import React from 'react';
import { TelemetryData } from '../types';
import { SPARKLINE_HISTORY_LENGTH } from '../constants';

interface DashboardProps {
  visible: boolean;
  telemetry: TelemetryData | null;
}

/**
 * Componente gráfico Sparkline (SVG ligero).
 * Renderiza una línea de tendencia simple sin ejes.
 */
const Sparkline = ({ data, color, height = 32 }: { data: number[], color: string, height?: number }) => {
  if (data.length < 2) return null;

  const max = 100; // Porcentajes siempre 0-100
  const min = 0;
  const width = 100;

  const points = data.map((d, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((d - min) / (max - min)) * height;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ overflow: 'visible' }}>
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        points={points}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
};

/**
 * Panel de métricas del sistema en tiempo real.
 * Muestra RAM, CPU y GPU con gráficos históricos pequeños.
 */
export const Dashboard = React.memo(({ telemetry, visible }: DashboardProps) => {
  // Acumular historial localmente para sparklines
  const [cpuHistory, setCpuHistory] = React.useState<number[]>([]);
  const [ramHistory, setRamHistory] = React.useState<number[]>([]);
  // Fix: Initialize with null to ensure first update is captured
  const [prevTelemetry, setPrevTelemetry] = React.useState<TelemetryData | null>(null);

  // OPTIMIZACIÓN BOLT: State Update During Render (Derived State)
  // Reemplaza useEffect para evitar doble renderizado (Render -> Effect -> SetState -> Render)
  // Al actualizar el estado durante el render, React descarta el output actual y re-renderiza inmediatamente (1 solo commit).
  if (telemetry !== prevTelemetry) {
    setPrevTelemetry(telemetry);
    if (telemetry) {
      setCpuHistory(prev => [...prev, telemetry.cpu.percent].slice(-SPARKLINE_HISTORY_LENGTH));
      setRamHistory(prev => [...prev, telemetry.ram.percent].slice(-SPARKLINE_HISTORY_LENGTH));
    }
  }

  if (!visible || !telemetry) return null;

  return (
    <div className="dashboard-grid">

      {/* Tarjeta RAM */}
      <div className="dashboard-card">
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div className="label">RAM Usage</div>
          <div className="card-value-large">
            {telemetry.ram.used_gb.toFixed(1)} <span className="card-subtext">/ {telemetry.ram.total_gb} GB</span>
          </div>
        </div>

        <div className="sparkline-container">
          <Sparkline data={ramHistory} color="var(--fg-primary)" />
        </div>
      </div>

      {/* Tarjeta CPU */}
      <div className="dashboard-card">
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div className="label">CPU Load</div>
          <div className="card-value-large">
            {telemetry.cpu.percent.toFixed(1)}%
          </div>
        </div>

        <div className="sparkline-container">
          <Sparkline
            data={cpuHistory}
            color={telemetry.cpu.percent > 80 ? 'var(--warning)' : 'var(--fg-primary)'}
          />
        </div>
      </div>

      {/* Tarjeta GPU (Ancho completo si existe) */}
      {telemetry.gpu && (
        <div className="dashboard-card dashboard-card-full">
          <div>
            <div className="label">GPU VRAM</div>
            <div style={{ fontSize: '16px', fontWeight: 600 }}>
              {telemetry.gpu.vram_used_mb} MB
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div className="label">Temp</div>
            <div style={{ fontSize: '16px', fontWeight: 600 }}>
              {telemetry.gpu.temp_c}°C
            </div>
          </div>
        </div>
      )}

      {/* Barra de Estado (Placeholder) */}
      <div className="dashboard-status-bar">
        <span>Status: Online</span>
        <span>•</span>
        <span>Latency: &lt;1ms</span>
      </div>

    </div>
  );
});
