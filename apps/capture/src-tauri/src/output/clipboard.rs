//! Wrapper de arboard para operaciones de clipboard.
//!
//! Proporciona una interfaz simple para copiar texto al clipboard del sistema.

use arboard::Clipboard;

/// Administrador de clipboard para copiar texto transcrito
pub struct ClipboardManager {
    /// Instancia de arboard Clipboard
    clipboard: Clipboard,
}

impl ClipboardManager {
    /// Crea un nuevo administrador de clipboard
    pub fn new() -> anyhow::Result<Self> {
        let clipboard = Clipboard::new()
            .map_err(|e| anyhow::anyhow!("Error inicializando clipboard: {}", e))?;

        Ok(Self { clipboard })
    }

    /// Copia texto al clipboard
    pub fn set_text(&mut self, text: &str) -> anyhow::Result<()> {
        self.clipboard
            .set_text(text)
            .map_err(|e| anyhow::anyhow!("Error copiando al clipboard: {}", e))?;

        log::info!("Texto copiado al clipboard: {} caracteres", text.len());
        Ok(())
    }

    /// Lee texto del clipboard
    pub fn get_text(&mut self) -> anyhow::Result<String> {
        self.clipboard
            .get_text()
            .map_err(|e| anyhow::anyhow!("Error leyendo clipboard: {}", e))
    }

    /// Limpia el clipboard
    pub fn clear(&mut self) -> anyhow::Result<()> {
        self.clipboard
            .clear()
            .map_err(|e| anyhow::anyhow!("Error limpiando clipboard: {}", e))
    }
}

/// Copia texto al clipboard en una sola llamada (utility function)
/// Util para operaciones unicas sin mantener estado
pub fn copy_to_clipboard(text: &str) -> anyhow::Result<()> {
    let mut manager = ClipboardManager::new()?;
    manager.set_text(text)
}

#[cfg(test)]
mod tests {
    use super::*;

    // Nota: Estos tests requieren un display server (X11/Wayland) en Linux
    // Se ejecutan solo si hay clipboard disponible

    #[test]
    #[ignore] // Ignorar en CI sin display
    fn test_clipboard_roundtrip() {
        let mut clipboard = ClipboardManager::new().expect("No se pudo inicializar clipboard");
        
        let test_text = "Texto de prueba para clipboard";
        clipboard.set_text(test_text).expect("Error escribiendo");
        
        let read_text = clipboard.get_text().expect("Error leyendo");
        assert_eq!(read_text, test_text);
    }
}
