import React from "react";
import { TabBar } from "./TabBar";
import { NoteEditor } from "./NoteEditor";
import { NotesState } from "../types";
import { NotesActions } from "../hooks/useNotes";
import { Status } from "../types";
import { MAX_NOTES } from "../constants";

interface StudioProps {
  notesState: NotesState;
  notesActions: NotesActions;
  status: Status;
  onRefine: () => void;
  onTogglePause: () => void;
}

/**
 * Componente principal del Studio de notas.
 * Integra TabBar para navegación y NoteEditor para edición.
 */
export const Studio = React.memo(
  ({
    notesState,
    notesActions,
    status,
    onRefine,
    onTogglePause,
  }: StudioProps) => {
    const activeNote = notesActions.getActiveNote();

    return (
      <div className="studio-container">
        <TabBar
          notes={notesState.notes}
          activeNoteId={notesState.activeNoteId}
          onSelectNote={notesActions.setActiveNote}
          onCreateNote={notesActions.createNote}
          onCloseNote={notesActions.deleteNote}
          onRenameNote={notesActions.renameNote}
          onReorderNotes={notesActions.reorderNotes}
          maxNotes={MAX_NOTES}
        />

        {activeNote ? (
          <NoteEditor
            note={activeNote}
            status={status}
            onContentChange={notesActions.updateActiveNoteContent}
            onRefine={onRefine}
            onTogglePause={onTogglePause}
          />
        ) : (
          <div className="studio-empty">
            <p>No hay notas abiertas</p>
            <button className="btn-primary" onClick={notesActions.createNote}>
              Crear nueva nota
            </button>
          </div>
        )}
      </div>
    );
  }
);

Studio.displayName = "Studio";
