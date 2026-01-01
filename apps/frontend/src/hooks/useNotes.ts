import { useState, useEffect, useCallback, useMemo } from "react";
import { Note, NotesState } from "../types";
import { NOTES_STORAGE_KEY, MAX_NOTES, DEFAULT_NOTE_TITLE } from "../constants";

/**
 * Crea una nueva nota con valores por defecto.
 */
function createNote(title?: string): Note {
  const now = Date.now();
  return {
    id: crypto.randomUUID(),
    title: title || DEFAULT_NOTE_TITLE,
    content: "",
    createdAt: now,
    updatedAt: now,
    language: "es",
  };
}

/**
 * Carga el estado de notas desde localStorage.
 * Si no hay datos o hay error, retorna estado inicial con una nota vacía.
 */
function loadNotesState(): NotesState {
  try {
    const saved = localStorage.getItem(NOTES_STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved) as NotesState;
      // Validación básica
      if (
        parsed.notes &&
        Array.isArray(parsed.notes) &&
        parsed.notes.length > 0
      ) {
        return parsed;
      }
    }
  } catch (e) {
    console.error("Failed to load notes from localStorage:", e);
  }

  // Estado inicial: una nota vacía
  const initialNote = createNote();
  return {
    notes: [initialNote],
    activeNoteId: initialNote.id,
  };
}

/**
 * Persiste el estado de notas en localStorage.
 */
function saveNotesState(state: NotesState): void {
  try {
    localStorage.setItem(NOTES_STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    console.error("Failed to save notes to localStorage:", e);
  }
}

export interface NotesActions {
  /** Crea una nueva nota y la activa */
  createNote: () => void;
  /** Elimina una nota por su ID */
  deleteNote: (noteId: string) => void;
  /** Cambia la nota activa */
  setActiveNote: (noteId: string) => void;
  /** Actualiza el contenido de la nota activa */
  updateActiveNoteContent: (content: string) => void;
  /** Renombra una nota */
  renameNote: (noteId: string, newTitle: string) => void;
  /** Obtiene la nota activa */
  getActiveNote: () => Note | null;
}

/**
 * Hook para gestionar el estado de múltiples notas del Studio.
 * Persiste automáticamente en localStorage.
 */
export function useNotes(): [NotesState, NotesActions] {
  const [state, setState] = useState<NotesState>(loadNotesState);

  // Persistir cambios en localStorage
  useEffect(() => {
    saveNotesState(state);
  }, [state]);

  const createNoteAction = useCallback(() => {
    setState((prev) => {
      if (prev.notes.length >= MAX_NOTES) {
        console.warn(`Cannot create more than ${MAX_NOTES} notes`);
        return prev;
      }

      const newNote = createNote();
      return {
        notes: [...prev.notes, newNote],
        activeNoteId: newNote.id,
      };
    });
  }, []);

  const deleteNote = useCallback((noteId: string) => {
    setState((prev) => {
      // No permitir eliminar la última nota
      if (prev.notes.length <= 1) {
        return prev;
      }

      const noteIndex = prev.notes.findIndex((n) => n.id === noteId);
      if (noteIndex === -1) return prev;

      const newNotes = prev.notes.filter((n) => n.id !== noteId);

      // Si eliminamos la nota activa, activar otra
      let newActiveId = prev.activeNoteId;
      if (prev.activeNoteId === noteId) {
        // Preferir la siguiente, o la anterior si era la última
        const newIndex = Math.min(noteIndex, newNotes.length - 1);
        const targetNote = newNotes[newIndex];
        newActiveId = targetNote ? targetNote.id : newNotes[0]?.id ?? null;
      }

      return {
        notes: newNotes,
        activeNoteId: newActiveId,
      };
    });
  }, []);

  const setActiveNote = useCallback((noteId: string) => {
    setState((prev) => {
      if (prev.activeNoteId === noteId) return prev;
      if (!prev.notes.find((n) => n.id === noteId)) return prev;
      return { ...prev, activeNoteId: noteId };
    });
  }, []);

  const updateActiveNoteContent = useCallback((content: string) => {
    setState((prev) => {
      if (!prev.activeNoteId) return prev;

      const updatedNotes = prev.notes.map((note) =>
        note.id === prev.activeNoteId
          ? { ...note, content, updatedAt: Date.now() }
          : note
      );

      return { ...prev, notes: updatedNotes };
    });
  }, []);

  const renameNote = useCallback((noteId: string, newTitle: string) => {
    setState((prev) => {
      const updatedNotes = prev.notes.map((note) =>
        note.id === noteId
          ? { ...note, title: newTitle, updatedAt: Date.now() }
          : note
      );

      return { ...prev, notes: updatedNotes };
    });
  }, []);

  const getActiveNote = useCallback((): Note | null => {
    return state.notes.find((n) => n.id === state.activeNoteId) || null;
  }, [state.notes, state.activeNoteId]);

  const actions: NotesActions = useMemo(
    () => ({
      createNote: createNoteAction,
      deleteNote,
      setActiveNote,
      updateActiveNoteContent,
      renameNote,
      getActiveNote,
    }),
    [
      createNoteAction,
      deleteNote,
      setActiveNote,
      updateActiveNoteContent,
      renameNote,
      getActiveNote,
    ]
  );

  return [state, actions];
}
