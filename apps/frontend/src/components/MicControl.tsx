import React from 'react';
import { MicIcon, StopIcon } from "../assets/Icons";
import { Status } from "../types";

interface MicControlProps {
    status: Status;
    onToggleRecord: () => void;
}

export const MicControl = React.memo(({ status, onToggleRecord }: MicControlProps) => {
    const isRecording = status === "recording";
    const isDisabled = status === "transcribing" || status === "processing" || status === "disconnected" || status === "paused";

    return (
        <div className="mic-float">
            <button
                className={`mic-btn ${isRecording ? "recording" : ""}`}
                onClick={onToggleRecord}
                disabled={isDisabled}
                aria-label={isRecording ? "Stop recording" : "Start recording"}
            >
                {isRecording ? <StopIcon /> : <MicIcon />}
            </button>
        </div>
    );
});
