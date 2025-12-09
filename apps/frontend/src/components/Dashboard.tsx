
import React from 'react';
import styles from './Dashboard.module.css';

interface MetricCardProps {
  title: string;
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
    <div className={styles.metricCard}>
      <div className={styles.metricHeader}>
        {icon}
        <span>{title}</span>
      </div>
      <div className={styles.metricValue} style={{ color: getStatusColor() }}>
        {value}<span className={styles.metricUnit}>{unit}</span>
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
    <div className={styles.dashboardGrid}>
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
