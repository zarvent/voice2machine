import React from 'react';
import { MicIcon, StopIcon } from "../assets/Icons";
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
    // Deshabilitar botón si el sistema está ocupado o desconectado
    // Deshabilitar botón si el sistema está ocupado o desconectado
    const isDisabled = status === "transcribing" || status === "processing" || status === "disconnected" || status === "paused";

    const getTooltip = () => {
        if (status === "disconnected") return "Sistema desconectado - Verifique el daemon";
        if (status === "transcribing") return "Transcribiendo audio...";
        if (status === "processing") return "Procesando texto...";
        if (status === "paused") return "Sistema pausado - Reanudar para grabar";
        if (isRecording) return "Click para detener";
        return "Click para grabar";
    };

    return (
        <div className="mic-float">
            <button
                className={`mic-btn ${isRecording ? "recording" : ""}`}
                onClick={onToggleRecord}
                disabled={isDisabled}
                aria-label={isRecording ? "Detener grabación" : "Iniciar grabación"}
                title={getTooltip()}
            >
                {isRecording ? <StopIcon /> : <MicIcon />}
            </button>
        </div>
    );
});
