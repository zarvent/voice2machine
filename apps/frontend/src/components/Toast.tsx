import React, { useEffect, useState } from 'react';

export type ToastType = 'success' | 'error' | 'info';

interface ToastProps {
    message: string;
    type: ToastType;
    onDismiss: () => void;
    duration?: number;
}

export const Toast: React.FC<ToastProps> = ({ message, type, onDismiss, duration = 3000 }) => {
    const [visible, setVisible] = useState(true);

    const handleClose = () => {
        setVisible(false);
        setTimeout(onDismiss, 200); // Wait for exit animation
    };

    useEffect(() => {
        const timer = setTimeout(() => {
            setVisible(false);
            setTimeout(onDismiss, 200);
        }, duration);
        return () => clearTimeout(timer);
    }, [duration, onDismiss]);

    const getIcon = () => {
        switch (type) {
            case 'success': return '✓';
            case 'error': return '✕';
            case 'info': return 'ℹ';
        }
    };

    const getColor = () => {
        switch (type) {
            case 'success': return 'var(--success)';
            case 'error': return 'var(--error)';
            default: return 'var(--fg-secondary)';
        }
    };

    // Accessibility attributes based on type
    const role = type === 'error' ? 'alert' : 'status';
    const ariaLive = type === 'error' ? 'assertive' : 'polite';

    return (
        <div
            className="toast"
            role={role}
            aria-live={ariaLive}
            aria-atomic="true"
            style={{
                opacity: visible ? 1 : 0,
                transform: visible ? 'translateY(0)' : 'translateY(10px)',
                transition: 'all 0.2s ease',
                borderLeft: `3px solid ${getColor()}`,
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                paddingRight: '32px', // Space for close button
                position: 'relative'
            }}
        >
            <span style={{ color: getColor(), fontWeight: 'bold', fontSize: '1.2em' }} aria-hidden="true">{getIcon()}</span>
            <span style={{ flex: 1 }}>{message}</span>

            <button
                onClick={handleClose}
                aria-label="Cerrar notificación"
                style={{
                    position: 'absolute',
                    right: '8px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--fg-secondary)',
                    cursor: 'pointer',
                    fontSize: '18px',
                    padding: '4px',
                    lineHeight: 1,
                    opacity: 0.6
                }}
                onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                onMouseLeave={(e) => e.currentTarget.style.opacity = '0.6'}
            >
                ×
            </button>
        </div>
    );
};
