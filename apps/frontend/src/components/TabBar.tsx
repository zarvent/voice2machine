import React, { useState, useCallback, useRef } from "react";
import { Note } from "../types";

interface TabBarProps {
  notes: Note[];
  activeNoteId: string | null;
  onSelectNote: (noteId: string) => void;
  onCreateNote: () => void;
  onCloseNote: (noteId: string) => void;
  onRenameNote: (noteId: string, newTitle: string) => void;
  onReorderNotes: (notes: Note[]) => void;
  maxNotes: number;
}

/**
 * Barra de tabs horizontal para navegar entre múltiples notas.
 * Soporta drag & drop para reordenar, renombrado inline, y atajos de teclado.
 */
export const TabBar = React.memo(
  ({
    notes,
    activeNoteId,
    onSelectNote,
    onCreateNote,
    onCloseNote,
    onRenameNote,
    onReorderNotes,
    maxNotes,
  }: TabBarProps) => {
    const [editingTabId, setEditingTabId] = useState<string | null>(null);
    const [editValue, setEditValue] = useState("");
    const [draggedId, setDraggedId] = useState<string | null>(null);
    const [dragOverId, setDragOverId] = useState<string | null>(null);
    const dragCounter = useRef(0);

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

    // --- DRAG & DROP HANDLERS ---
    const handleDragStart = useCallback(
      (e: React.DragEvent, noteId: string) => {
        setDraggedId(noteId);
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", noteId);
        // Añadir clase visual después de un pequeño delay
        requestAnimationFrame(() => {
          const target = e.target as HTMLElement;
          target.classList.add("tab--dragging");
        });
      },
      []
    );

    const handleDragEnd = useCallback((e: React.DragEvent) => {
      setDraggedId(null);
      setDragOverId(null);
      dragCounter.current = 0;
      (e.target as HTMLElement).classList.remove("tab--dragging");
    }, []);

    const handleDragEnter = useCallback(
      (e: React.DragEvent, noteId: string) => {
        e.preventDefault();
        dragCounter.current++;
        if (noteId !== draggedId) {
          setDragOverId(noteId);
        }
      },
      [draggedId]
    );

    const handleDragLeave = useCallback(() => {
      dragCounter.current--;
      if (dragCounter.current === 0) {
        setDragOverId(null);
      }
    }, []);

    const handleDragOver = useCallback((e: React.DragEvent) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
    }, []);

    const handleDrop = useCallback(
      (e: React.DragEvent, targetId: string) => {
        e.preventDefault();
        const sourceId = e.dataTransfer.getData("text/plain");

        if (sourceId && sourceId !== targetId) {
          const sourceIndex = notes.findIndex((n) => n.id === sourceId);
          const targetIndex = notes.findIndex((n) => n.id === targetId);

          if (sourceIndex !== -1 && targetIndex !== -1) {
            const newNotes = [...notes];
            const [removed] = newNotes.splice(sourceIndex, 1);
            if (removed) {
              newNotes.splice(targetIndex, 0, removed);
              onReorderNotes(newNotes);
            }
          }
        }

        setDraggedId(null);
        setDragOverId(null);
        dragCounter.current = 0;
      },
      [notes, onReorderNotes]
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
            className={`tab ${note.id === activeNoteId ? "tab--active" : ""} ${
              note.id === draggedId ? "tab--dragging" : ""
            } ${note.id === dragOverId ? "tab--drag-over" : ""}`}
            onClick={() => onSelectNote(note.id)}
            onDoubleClick={() => handleDoubleClick(note)}
            onKeyDown={(e) => e.key === "Enter" && onSelectNote(note.id)}
            draggable={editingTabId !== note.id}
            onDragStart={(e) => handleDragStart(e, note.id)}
            onDragEnd={handleDragEnd}
            onDragEnter={(e) => handleDragEnter(e, note.id)}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, note.id)}
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
                    title="Cerrar nota (Ctrl+W)"
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
            aria-label="Crear nueva nota (Ctrl+T)"
            title="Nueva nota (Ctrl+T)"
          >
            +
          </button>
        )}
      </div>
    );
  }
);

TabBar.displayName = "TabBar";
