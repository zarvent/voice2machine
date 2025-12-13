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

/**
 * Panel principal de visualización y edición de la transcripción.
 * Contiene el área de texto y la barra de acciones (copiar, refinar, pausar).
 */
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
            {/* Barra de herramientas superior */}
            <div className="action-bar" role="toolbar" aria-label="Editor controls">
                <button
                    className="btn-secondary"
                    onClick={onCopy}
                    disabled={!transcription}
                    aria-label="Copiar texto al portapapeles"
                >
                    <CopyIcon /> {lastCopied ? "Copiado" : "Copiar"}
                </button>
                <button
                    className="btn-secondary"
                    onClick={onRefine}
                    disabled={!transcription || status !== "idle"}
                    title="Refinar gramática y estilo con IA"
                    aria-label="Refinar con Inteligencia Artificial"
                >
                    <SparklesIcon /> Mejorar con IA
                </button>
                <button
                    className="btn-secondary"
                    onClick={onTogglePause}
                    disabled={status === "disconnected"}
                    aria-pressed={status === "paused"}
                >
                    {status === "paused" ? <PlayIcon /> : <PauseIcon />}
                    {status === "paused" ? "Reanudar" : "Pausar Sistema"}
                </button>
            </div>

            {/* Área de texto editable */}
            <textarea
                className="editor"
                value={transcription}
                onChange={(e) => onTranscriptionChange(e.target.value)}
                placeholder={status === "paused" ? "Sistema pausado..." : "Empieza a hablar para transcribir..."}
                spellCheck={false}
                disabled={status === "paused"}
                aria-label="Texto transcrito"
            />
        </div>
    );
});
