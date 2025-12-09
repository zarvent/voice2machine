
import React from 'react';

interface MetricCardProps {
  title: String;
  value: string | number;
  unit?: string;
  icon?: React.ReactNode;
  status?: 'normal' | 'warning' | 'critical';
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, unit, icon, status = 'normal' }) => {
  const getStatusColor = () => {
    switch (status) {
      case 'warning': return 'var(--color-warning)';
      case 'critical': return 'var(--color-error)';
      default: return 'var(--color-text-secondary)';
    }
  };

  return (
    <div className="metric-card" style={{
      background: 'rgba(255, 255, 255, 0.05)',
      borderRadius: '8px',
      padding: '12px',
      display: 'flex',
      flexDirection: 'column',
      gap: '4px',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      backdropFilter: 'blur(4px)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
        {icon}
        <span>{title}</span>
      </div>
      <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: getStatusColor() }}>
        {value}<span style={{ fontSize: '0.8rem', marginLeft: '2px', opacity: 0.7 }}>{unit}</span>
      </div>
    </div>
  );
};

interface TelemetryData {
  ram: {
    used_gb: number;
    total_gb: number;
    percent: number;
  };
  cpu: {
    percent: number;
  };
  gpu?: {
    vram_used_mb: number;
    temp_c: number;
  };
}

interface DashboardProps {
  telemetry: TelemetryData | null;
  visible: boolean;
}

export const Dashboard: React.FC<DashboardProps> = ({ telemetry, visible }) => {
  if (!visible || !telemetry) return null;

  return (
    <div className="dashboard-grid" style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
      gap: '12px',
      margin: '20px 0',
      animation: 'fadeIn 0.3s ease'
    }}>
      <MetricCard
        title="RAM System"
        value={telemetry.ram.used_gb}
        unit={`/ ${telemetry.ram.total_gb} GB`}
        status={telemetry.ram.percent > 80 ? 'warning' : 'normal'}
      />
      <MetricCard
        title="CPU Load"
        value={telemetry.cpu.percent}
        unit="%"
        status={telemetry.cpu.percent > 90 ? 'critical' : 'normal'}
      />
      {telemetry.gpu && (
        <>
          <MetricCard
            title="GPU VRAM"
            value={telemetry.gpu.vram_used_mb}
            unit="MB"
          />
          <MetricCard
            title="GPU Temp"
            value={telemetry.gpu.temp_c}
            unit="°C"
          />
        </>
      )}
    </div>
  );
};
