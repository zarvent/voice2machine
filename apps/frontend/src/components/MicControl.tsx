import React from 'react';
import { MicIcon, StopIcon, LoaderIcon } from "../assets/Icons";
import { Status } from "../types";

interface MicControlProps {
    status: Status;
    onToggleRecord: () => void;
}

/**
 * Botón flotante principal para control de grabación.
 * Cambia de apariencia (rojo/normal) y de icono (mic/stop) según el estado.
 */
export const MicControl = React.memo(({ status, onToggleRecord }: MicControlProps) => {
    const isRecording = status === "recording";
    const isProcessing = status === "transcribing" || status === "processing";

    // Deshabilitar botón si el sistema está desconectado o pausado
    // Nota: 'processing' no lo deshabilita visualmente para mostrar el spinner,
    // pero el click no hará nada útil (o podría cancelar).
    const isDisabled = status === "disconnected" || status === "paused" || isProcessing;

    const getTooltip = () => {
        if (status === "disconnected") return "Sistema desconectado - Verifique el daemon";
        if (status === "transcribing") return "Transcribiendo audio...";
        if (status === "processing") return "Procesando texto...";
        if (status === "paused") return "Sistema pausado - Reanudar para grabar";
        if (isRecording) return "Click para detener (Ctrl+Espacio)";
        return "Click para grabar (Ctrl+Espacio)";
    };

    const getIcon = () => {
        if (isProcessing) return <LoaderIcon />;
        if (isRecording) return <StopIcon />;
        return <MicIcon />;
    };

    const getAriaLabel = () => {
        if (isProcessing) return "Procesando...";
        if (isRecording) return "Detener grabación";
        return "Iniciar grabación";
    };

    return (
        <div className="mic-float">
            <button
                className={`mic-btn ${isRecording ? "recording" : ""} ${isProcessing ? "processing" : ""}`}
                onClick={onToggleRecord}
                disabled={isDisabled}
                aria-label={getAriaLabel()}
                title={getTooltip()}
            >
                {getIcon()}
            </button>
        </div>
    );
});
