import React, { useState, useEffect, useCallback } from "react";
import { Note } from "../types";
import { Status } from "../types";
import { ExportMenu } from "./ExportMenu";
import { TranslateButton } from "./TranslateButton";
import {
  SparklesIcon,
  PauseIcon,
  PlayIcon,
  TrashIcon,
  LoaderIcon,
} from "../assets/Icons";

interface NoteEditorProps {
  note: Note;
  status: Status;
  onContentChange: (content: string) => void;
  onRefine: () => void;
  onTogglePause: () => void;
}

/**
 * Editor individual de nota con toolbar completa.
 * Evolución de TranscriptionArea para soportar el sistema de tabs.
 */
export const NoteEditor = React.memo(
  ({
    note,
    status,
    onContentChange,
    onRefine,
    onTogglePause,
  }: NoteEditorProps) => {
    const charCount = note.content.length;
    const wordCount = note.content.trim()
      ? note.content.trim().split(/\s+/).length
      : 0;
    const isProcessing = status === "processing";
    const [confirmClear, setConfirmClear] = useState(false);

    // Resetear confirmación después de 3 segundos
    useEffect(() => {
      if (confirmClear) {
        const timer = setTimeout(() => setConfirmClear(false), 3000);
        return () => clearTimeout(timer);
      }
    }, [confirmClear]);

    const handleClearClick = useCallback(() => {
      if (confirmClear) {
        onContentChange("");
        setConfirmClear(false);
      } else {
        setConfirmClear(true);
      }
    }, [confirmClear, onContentChange]);

    const handleTextChange = useCallback(
      (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        onContentChange(e.target.value);
      },
      [onContentChange]
    );

    return (
      <div className="note-editor">
        {/* Barra de herramientas */}
        <div
          className="editor-toolbar"
          role="toolbar"
          aria-label="Editor controls"
        >
          {/* Grupo izquierdo: Acciones principales */}
          <div className="toolbar-group toolbar-group--left">
            <button
              className="btn-secondary"
              onClick={onRefine}
              disabled={!note.content || status !== "idle"}
              title="Refinar gramática y estilo con IA"
              aria-label={
                isProcessing
                  ? "Refinando texto..."
                  : "Refinar con Inteligencia Artificial"
              }
            >
              {isProcessing ? (
                <div className="spin-anim btn-loader">
                  <LoaderIcon />
                </div>
              ) : (
                <SparklesIcon />
              )}
              {isProcessing ? "Mejorando..." : "Mejorar con IA"}
            </button>

            <button
              className="btn-secondary"
              onClick={handleClearClick}
              disabled={!note.content || status === "paused"}
              title={
                confirmClear
                  ? "Click otra vez para confirmar"
                  : "Borrar todo el texto"
              }
              aria-label={
                confirmClear ? "Confirmar borrado" : "Borrar contenido"
              }
              style={
                confirmClear
                  ? { borderColor: "var(--error)", color: "var(--error)" }
                  : undefined
              }
            >
              <TrashIcon />
              {confirmClear ? "¿Seguro?" : "Limpiar"}
            </button>

            <button
              className="btn-secondary"
              onClick={onTogglePause}
              disabled={status === "disconnected"}
              aria-pressed={status === "paused"}
              aria-label={
                status === "paused" ? "Reanudar sistema" : "Pausar sistema"
              }
            >
              {status === "paused" ? <PlayIcon /> : <PauseIcon />}
              {status === "paused" ? "Reanudar" : "Pausar"}
            </button>
          </div>

          {/* Grupo derecho: Exportación y Traducción */}
          <div className="toolbar-group toolbar-group--right">
            <TranslateButton
              disabled={!note.content || status === "paused"}
              currentLanguage={note.language || "es"}
            />

            <ExportMenu
              content={note.content}
              noteTitle={note.title}
              disabled={status === "paused"}
            />
          </div>
        </div>

        {/* Área de texto editable */}
        <div className="editor-container">
          <textarea
            className="editor"
            value={note.content}
            onChange={handleTextChange}
            placeholder={
              status === "paused"
                ? "Sistema pausado..."
                : "Empieza a hablar para transcribir..."
            }
            spellCheck={false}
            disabled={status === "paused"}
            aria-label="Texto de la nota"
          />

          {/* Contador de caracteres/palabras */}
          <div className="char-count" aria-live="polite">
            {charCount > 0 && (
              <>
                <span>
                  {charCount} {charCount === 1 ? "carácter" : "caracteres"}
                </span>
                <span className="count-separator">•</span>
                <span>
                  {wordCount} {wordCount === 1 ? "palabra" : "palabras"}
                </span>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }
);

NoteEditor.displayName = "NoteEditor";
