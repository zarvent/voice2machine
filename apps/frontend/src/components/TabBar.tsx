import React, { useState, useCallback } from "react";
import { Note } from "../types";

interface TabBarProps {
  notes: Note[];
  activeNoteId: string | null;
  onSelectNote: (noteId: string) => void;
  onCreateNote: () => void;
  onCloseNote: (noteId: string) => void;
  onRenameNote: (noteId: string, newTitle: string) => void;
  maxNotes: number;
}

/**
 * Barra de tabs horizontal para navegar entre múltiples notas.
 * Estilo inspirado en Chrome tabs.
 */
export const TabBar = React.memo(
  ({
    notes,
    activeNoteId,
    onSelectNote,
    onCreateNote,
    onCloseNote,
    onRenameNote,
    maxNotes,
  }: TabBarProps) => {
    const [editingTabId, setEditingTabId] = useState<string | null>(null);
    const [editValue, setEditValue] = useState("");

    const handleDoubleClick = useCallback((note: Note) => {
      setEditingTabId(note.id);
      setEditValue(note.title);
    }, []);

    const handleRenameSubmit = useCallback(
      (noteId: string) => {
        if (editValue.trim()) {
          onRenameNote(noteId, editValue.trim());
        }
        setEditingTabId(null);
      },
      [editValue, onRenameNote]
    );

    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent, noteId: string) => {
        if (e.key === "Enter") {
          handleRenameSubmit(noteId);
        } else if (e.key === "Escape") {
          setEditingTabId(null);
        }
      },
      [handleRenameSubmit]
    );

    const handleCloseClick = useCallback(
      (e: React.MouseEvent, noteId: string) => {
        e.stopPropagation();
        onCloseNote(noteId);
      },
      [onCloseNote]
    );

    const canAddNote = notes.length < maxNotes;

    return (
      <div className="tab-bar" role="tablist" aria-label="Notas abiertas">
        {notes.map((note) => (
          <div
            key={note.id}
            role="tab"
            aria-selected={note.id === activeNoteId}
            tabIndex={note.id === activeNoteId ? 0 : -1}
            className={`tab ${note.id === activeNoteId ? "tab--active" : ""}`}
            onClick={() => onSelectNote(note.id)}
            onDoubleClick={() => handleDoubleClick(note)}
            onKeyDown={(e) => e.key === "Enter" && onSelectNote(note.id)}
          >
            {editingTabId === note.id ? (
              <input
                type="text"
                className="tab-rename-input"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onBlur={() => handleRenameSubmit(note.id)}
                onKeyDown={(e) => handleKeyDown(e, note.id)}
                autoFocus
                aria-label="Renombrar nota"
              />
            ) : (
              <>
                <span className="tab-title">{note.title}</span>
                {notes.length > 1 && (
                  <button
                    className="tab-close"
                    onClick={(e) => handleCloseClick(e, note.id)}
                    aria-label={`Cerrar ${note.title}`}
                    title="Cerrar nota"
                  >
                    ✕
                  </button>
                )}
              </>
            )}
          </div>
        ))}

        {canAddNote && (
          <button
            className="tab-add"
            onClick={onCreateNote}
            aria-label="Crear nueva nota"
            title="Nueva nota"
          >
            +
          </button>
        )}
      </div>
    );
  }
);

TabBar.displayName = "TabBar";
