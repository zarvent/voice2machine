import React from 'react';
import { CopyIcon, SparklesIcon, PauseIcon, PlayIcon } from "../assets/Icons";
import { Status } from "../types";

interface TranscriptionAreaProps {
    transcription: string;
    status: Status;
    lastCopied: boolean;
    onTranscriptionChange: (text: string) => void;
    onCopy: () => void;
    onRefine: () => void;
    onTogglePause: () => void;
}

export const TranscriptionArea = React.memo(({
    transcription,
    status,
    lastCopied,
    onTranscriptionChange,
    onCopy,
    onRefine,
    onTogglePause
}: TranscriptionAreaProps) => {
    return (
        <div className="transcription-panel">
            <div className="action-bar">
                <button
                    className="btn-secondary"
                    onClick={onCopy}
                    disabled={!transcription}
                >
                    <CopyIcon /> {lastCopied ? "Copied" : "Copy Text"}
                </button>
                <button
                    className="btn-secondary"
                    onClick={onRefine}
                    disabled={!transcription || status !== "idle"}
                    title="Refine with LLM"
                >
                    <SparklesIcon /> AI Refine
                </button>
                <button
                    className="btn-secondary"
                    onClick={onTogglePause}
                    disabled={status === "disconnected"}
                >
                    {status === "paused" ? <PlayIcon /> : <PauseIcon />}
                    {status === "paused" ? "Resume" : "Pause System"}
                </button>
            </div>

            <textarea
                className="editor"
                value={transcription}
                onChange={(e) => onTranscriptionChange(e.target.value)}
                placeholder={status === "paused" ? "System paused..." : "Start speaking..."}
                spellCheck={false}
                disabled={status === "paused"}
            />
        </div>
    );
});
