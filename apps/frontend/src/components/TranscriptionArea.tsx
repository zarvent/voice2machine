import React from 'react';
import { CopyIcon, SparklesIcon, PauseIcon, PlayIcon } from "../assets/Icons";
import { Status } from "../hooks/useBackend";

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
        <>
            <div className="transcription-card">
                <textarea
                    value={transcription}
                    onChange={(e) => onTranscriptionChange(e.target.value)}
                    placeholder={status === "paused" ? "Sistema en pausa..." : "Habla o pega texto aquí..."}
                    spellCheck={false}
                    aria-label="Texto transcrito"
                    disabled={status === "paused"}
                />
            </div>

            <div className="action-bar">
                <button
                    className="btn-secondary"
                    onClick={onCopy}
                    disabled={!transcription}
                    aria-label={lastCopied ? "Texto copiado" : "Copiar texto al portapapeles"}
                >
                    <CopyIcon /> {lastCopied ? "¡Copiado!" : "Copiar"}
                </button>
                <button
                    className="btn-secondary"
                    onClick={onRefine}
                    disabled={!transcription || status !== "idle"}
                    aria-label="Refinar texto con inteligencia artificial"
                >
                    <SparklesIcon /> Refinar IA
                </button>
                <button
                    className="btn-secondary"
                    onClick={onTogglePause}
                    disabled={status === "disconnected"}
                    title={status === "paused" ? "Reanudar sistema" : "Pausar sistema para ahorrar energía"}
                >
                    {status === "paused" ? <PlayIcon /> : <PauseIcon />}
                    {status === "paused" ? "Reanudar" : "Pausar"}
                </button>
            </div>
        </>
    );
});
