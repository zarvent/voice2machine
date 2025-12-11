import React from 'react';
import { TelemetryData } from '../types';

interface DashboardProps {
  visible: boolean;
  telemetry: TelemetryData | null;
}

// Simple Sparkline Component (SVG)
const Sparkline = ({ data, color, height = 32 }: { data: number[], color: string, height?: number }) => {
  if (data.length < 2) return null;

  const max = 100; // Percentages always 0-100
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

export const Dashboard: React.FC<DashboardProps> = ({ telemetry, visible }) => {
  // Accumulate history locally for sparklines
  const [cpuHistory, setCpuHistory] = React.useState<number[]>([]);
  const [ramHistory, setRamHistory] = React.useState<number[]>([]);

  React.useEffect(() => {
    if (!telemetry) return;

    setCpuHistory(prev => {
      const next = [...prev, telemetry.cpu.percent];
      return next.slice(-20); // Keep last 20 points
    });

    setRamHistory(prev => {
      const next = [...prev, telemetry.ram.percent];
      return next.slice(-20);
    });

  }, [telemetry]); // Update when telemetry changes

  if (!visible || !telemetry) return null;

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(2, 1fr)',
      gap: '12px',
      padding: '0 20px 20px 20px',
      borderBottom: '1px solid var(--border-subtle)'
    }}>

      {/* RAM Card */}
      <div style={{
        background: 'var(--bg-surface)',
        padding: '12px',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-subtle)',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div className="label">RAM Usage</div>
          <div style={{ fontSize: '18px', fontWeight: 600, margin: '4px 0' }}>
            {telemetry.ram.used_gb.toFixed(1)} <span style={{ fontSize: '13px', color: 'var(--fg-secondary)', fontWeight: 400 }}>/ {telemetry.ram.total_gb} GB</span>
          </div>
        </div>

        {/* Sparkline Overlay */}
        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 32, opacity: 0.2 }}>
          <Sparkline data={ramHistory} color="var(--fg-primary)" />
        </div>
      </div>

      {/* CPU Card */}
      <div style={{
        background: 'var(--bg-surface)',
        padding: '12px',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-subtle)',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div className="label">CPU Load</div>
          <div style={{ fontSize: '18px', fontWeight: 600, margin: '4px 0' }}>
            {telemetry.cpu.percent.toFixed(1)}%
          </div>
        </div>

        {/* Sparkline Overlay */}
        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 32, opacity: 0.2 }}>
          <Sparkline
            data={cpuHistory}
            color={telemetry.cpu.percent > 80 ? 'var(--warning)' : 'var(--fg-primary)'}
          />
        </div>
      </div>

      {/* GPU Card (Full Width if present) */}
      {telemetry.gpu && (
        <div style={{
          gridColumn: '1 / -1',
          background: 'var(--bg-surface)',
          padding: '12px',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
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

      {/* Uptime / Stat (Dummy for now) */}
      <div style={{
        gridColumn: '1 / -1',
        display: 'flex',
        gap: '8px',
        fontSize: '12px',
        color: 'var(--fg-secondary)'
      }}>
        <span>System Status: Online</span>
        <span>•</span>
        <span>Latency: ~0ms</span>
      </div>

    </div>
  );
};
