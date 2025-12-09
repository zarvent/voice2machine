import React from 'react';
import { MicIcon, StopIcon } from "../assets/Icons";
import { Status } from "../hooks/useBackend";

interface MicControlProps {
    status: Status;
    onToggleRecord: () => void;
}

export const MicControl = React.memo(({ status, onToggleRecord }: MicControlProps) => {
    const isRecording = status === "recording";
    const isDisabled = status === "transcribing" || status === "processing" || status === "disconnected" || status === "paused";

    return (
        <div className="control-surface">
            <div className="mic-button-container">
                {/* Premium Wave Effects */}
                {isRecording && (
                    <>
                        <div className="wave-ring ring-1"></div>
                        <div className="wave-ring ring-2"></div>
                        <div className="wave-ring ring-3"></div>
                    </>
                )}

                <button
                    className={`mic-button ${isRecording ? "recording" : ""}`}
                    onClick={onToggleRecord}
                    disabled={isDisabled}
                    aria-label={isRecording ? "Detener grabación" : "Iniciar grabación"}
                >
                    {isRecording ? <StopIcon /> : <MicIcon />}
                </button>
            </div>
        </div>
    );
});
