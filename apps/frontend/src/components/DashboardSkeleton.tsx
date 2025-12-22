/**
 * Skeleton loading state for the Dashboard.
 * Displays pulsing placeholders for metrics cards.
 */
export const DashboardSkeleton = () => {
    return (
        <div className="dashboard-grid" aria-busy="true" aria-label="Loading metrics">
            {/* RAM Skeleton */}
            <div className="dashboard-card skeleton-pulse" style={{ height: '100px', gap: '8px' }}>
                <div style={{ width: '40%', height: '14px', background: 'var(--border-subtle)', borderRadius: '4px' }}></div>
                <div style={{ width: '80%', height: '24px', background: 'var(--border-subtle)', borderRadius: '4px' }}></div>
                <div style={{ width: '100%', height: '32px', marginTop: 'auto', background: 'var(--border-subtle)', borderRadius: '4px', opacity: 0.3 }}></div>
            </div>

            {/* CPU Skeleton */}
            <div className="dashboard-card skeleton-pulse" style={{ height: '100px', gap: '8px' }}>
                <div style={{ width: '40%', height: '14px', background: 'var(--border-subtle)', borderRadius: '4px' }}></div>
                <div style={{ width: '60%', height: '24px', background: 'var(--border-subtle)', borderRadius: '4px' }}></div>
                <div style={{ width: '100%', height: '32px', marginTop: 'auto', background: 'var(--border-subtle)', borderRadius: '4px', opacity: 0.3 }}></div>
            </div>

            {/* GPU Skeleton (Full Width) */}
            <div className="dashboard-card dashboard-card-full skeleton-pulse" style={{ height: '70px', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '40%' }}>
                    <div style={{ width: '60%', height: '14px', background: 'var(--border-subtle)', borderRadius: '4px' }}></div>
                    <div style={{ width: '80%', height: '20px', background: 'var(--border-subtle)', borderRadius: '4px' }}></div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '20%', alignItems: 'flex-end' }}>
                    <div style={{ width: '80%', height: '14px', background: 'var(--border-subtle)', borderRadius: '4px' }}></div>
                    <div style={{ width: '60%', height: '20px', background: 'var(--border-subtle)', borderRadius: '4px' }}></div>
                </div>
            </div>

            {/* Status Bar Skeleton */}
            <div className="dashboard-status-bar skeleton-pulse">
                 <div style={{ width: '120px', height: '12px', background: 'var(--border-subtle)', borderRadius: '4px' }}></div>
            </div>
        </div>
    );
};
