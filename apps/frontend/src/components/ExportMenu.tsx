import React, { useState, useRef, useEffect } from "react";

interface ExportMenuProps {
  content: string;
  noteTitle: string;
  disabled?: boolean;
}

/**
 * Menú dropdown para exportar contenido de nota.
 * Soporta: Portapapeles, TXT, Markdown.
 */
export const ExportMenu = React.memo(
  ({ content, noteTitle, disabled = false }: ExportMenuProps) => {
    const [isOpen, setIsOpen] = useState(false);
    const [copyFeedback, setCopyFeedback] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    // Cerrar al hacer click fuera
    useEffect(() => {
      const handleClickOutside = (e: MouseEvent) => {
        if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
          setIsOpen(false);
        }
      };

      if (isOpen) {
        document.addEventListener("mousedown", handleClickOutside);
      }
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }, [isOpen]);

    // Cerrar con Escape
    useEffect(() => {
      const handleEscape = (e: KeyboardEvent) => {
        if (e.key === "Escape") setIsOpen(false);
      };

      if (isOpen) {
        document.addEventListener("keydown", handleEscape);
      }
      return () => document.removeEventListener("keydown", handleEscape);
    }, [isOpen]);

    const handleCopyToClipboard = async () => {
      try {
        await navigator.clipboard.writeText(content);
        setCopyFeedback(true);
        setTimeout(() => setCopyFeedback(false), 2000);
        setIsOpen(false);
      } catch (err) {
        console.error("Failed to copy:", err);
      }
    };

    const handleExportTxt = async () => {
      try {
        // Importación dinámica de plugins de Tauri
        const { save } = await import("@tauri-apps/plugin-dialog");
        const { writeTextFile } = await import("@tauri-apps/plugin-fs");

        const filePath = await save({
          defaultPath: `${noteTitle.replace(/[^a-zA-Z0-9]/g, "_")}.txt`,
          filters: [{ name: "Text Files", extensions: ["txt"] }],
        });

        if (filePath) {
          await writeTextFile(filePath, content);
        }
        setIsOpen(false);
      } catch (err) {
        console.error("Failed to export TXT:", err);
        // Fallback: descargar como blob si Tauri no está disponible
        downloadAsFile(content, `${noteTitle}.txt`, "text/plain");
        setIsOpen(false);
      }
    };

    const handleExportMd = async () => {
      const mdContent = `# ${noteTitle}\n\n${content}`;

      try {
        const { save } = await import("@tauri-apps/plugin-dialog");
        const { writeTextFile } = await import("@tauri-apps/plugin-fs");

        const filePath = await save({
          defaultPath: `${noteTitle.replace(/[^a-zA-Z0-9]/g, "_")}.md`,
          filters: [{ name: "Markdown Files", extensions: ["md"] }],
        });

        if (filePath) {
          await writeTextFile(filePath, mdContent);
        }
        setIsOpen(false);
      } catch (err) {
        console.error("Failed to export MD:", err);
        downloadAsFile(mdContent, `${noteTitle}.md`, "text/markdown");
        setIsOpen(false);
      }
    };

    // Fallback para navegador sin Tauri
    const downloadAsFile = (
      text: string,
      filename: string,
      mimeType: string
    ) => {
      const blob = new Blob([text], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    };

    return (
      <div className="export-menu-container" ref={menuRef}>
        <button
          className="btn-secondary"
          onClick={() => setIsOpen(!isOpen)}
          disabled={disabled || !content}
          aria-haspopup="menu"
          aria-expanded={isOpen}
          aria-label="Exportar nota"
        >
          <ExportIcon />
          {copyFeedback ? "¡Copiado!" : "Exportar"}
        </button>

        {isOpen && (
          <div className="export-menu" role="menu">
            <button
              className="export-menu-item"
              onClick={handleCopyToClipboard}
              role="menuitem"
            >
              <span className="export-icon">📋</span>
              Copiar al portapapeles
            </button>
            <button
              className="export-menu-item"
              onClick={handleExportTxt}
              role="menuitem"
            >
              <span className="export-icon">📄</span>
              Guardar como TXT
            </button>
            <button
              className="export-menu-item"
              onClick={handleExportMd}
              role="menuitem"
            >
              <span className="export-icon">📝</span>
              Guardar como Markdown
            </button>
          </div>
        )}
      </div>
    );
  }
);

ExportMenu.displayName = "ExportMenu";

// Icono de exportar
const ExportIcon = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="17 8 12 3 7 8" />
    <line x1="12" y1="3" x2="12" y2="15" />
  </svg>
);
