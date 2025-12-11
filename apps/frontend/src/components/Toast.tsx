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

    useEffect(() => {
        const timer = setTimeout(() => {
            setVisible(false);
            setTimeout(onDismiss, 200); // Wait for exit animation
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

    return (
        <div
            className="toast"
            style={{
                opacity: visible ? 1 : 0,
                transform: visible ? 'translateY(0)' : 'translateY(10px)',
                transition: 'all 0.2s ease',
                borderLeft: `3px solid ${getColor()}`
            }}
        >
            <span style={{ color: getColor(), fontWeight: 'bold' }}>{getIcon()}</span>
            <span>{message}</span>
        </div>
    );
};
