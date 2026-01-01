import React, { useState, useCallback } from "react";

interface TranslateButtonProps {
  disabled?: boolean;
  currentLanguage?: "es" | "en";
  onTranslate?: (targetLang: "es" | "en") => void;
}

/**
 * Botón conceptual de traducción ES ↔ EN.
 * Actualmente muestra un toast informativo;
 * listo para integrarse cuando exista el backend de traducción.
 */
export const TranslateButton = React.memo(
  ({
    disabled = false,
    currentLanguage = "es",
    onTranslate,
  }: TranslateButtonProps) => {
    const [showToast, setShowToast] = useState(false);

    const targetLang = currentLanguage === "es" ? "en" : "es";
    const targetLabel = targetLang === "en" ? "English" : "Español";

    const handleClick = useCallback(() => {
      if (onTranslate) {
        onTranslate(targetLang);
      } else {
        // Comportamiento conceptual: mostrar toast
        setShowToast(true);
        setTimeout(() => setShowToast(false), 3000);
      }
    }, [onTranslate, targetLang]);

    return (
      <div className="translate-button-container">
        <button
          className="btn-secondary btn-translate"
          onClick={handleClick}
          disabled={disabled}
          data-lang={currentLanguage}
          aria-label={`Traducir a ${targetLabel}`}
          title={`Traducir a ${targetLabel}`}
        >
          <TranslateIcon />
          <span className="translate-label">
            {currentLanguage.toUpperCase()} → {targetLang.toUpperCase()}
          </span>
        </button>

        {showToast && (
          <div className="translate-toast" role="status" aria-live="polite">
            <span className="translate-toast-icon">🌐</span>
            <span>Traducción próximamente</span>
          </div>
        )}
      </div>
    );
  }
);

TranslateButton.displayName = "TranslateButton";

// Icono de traducción
const TranslateIcon = () => (
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
    <path d="M5 8l6 6" />
    <path d="M4 14l6-6 2-3" />
    <path d="M2 5h12" />
    <path d="M7 2v3" />
    <path d="M22 22l-5-10-5 10" />
    <path d="M14 18h6" />
  </svg>
);
