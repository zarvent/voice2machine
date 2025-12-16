import React, { useEffect, useState, useCallback } from 'react';

export type ToastType = 'success' | 'error' | 'info';

interface ToastProps {
    message: string;
    type: ToastType;
    onDismiss: () => void;
    duration?: number;
}

export const Toast: React.FC<ToastProps> = ({ message, type, onDismiss, duration = 3000 }) => {
    const [visible, setVisible] = useState(true);

    const handleClose = useCallback(() => {
        setVisible(false);
        setTimeout(onDismiss, 200); // Esperar a la animación de salida
    }, [onDismiss]);

    useEffect(() => {
        const timer = setTimeout(() => {
            handleClose();
        }, duration);
        return () => clearTimeout(timer);
    }, [duration, handleClose]);

    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                handleClose();
            }
        };
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [handleClose]);

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
                paddingRight: '32px', // Espacio para el botón de cerrar
                position: 'relative'
            }}
        >
            <span style={{ color: getColor(), fontWeight: 'bold', fontSize: '1.2em' }} aria-hidden="true">{getIcon()}</span>
            <span style={{ flex: 1 }}>{message}</span>

            <button
                onClick={handleClose}
                aria-label="Cerrar notificación"
                className="toast-close"
            >
                ×
            </button>
        </div>
    );
};
