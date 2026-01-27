//! Wrapper de arboard para operaciones de clipboard.
//!
//! Proporciona una interfaz simple para copiar texto al clipboard del sistema.
//!
//! ## Nota sobre Linux
//! En Linux (X11/Wayland), arboard usa un modelo de "selection ownership".
//! La aplicacion que puso el contenido debe mantener la instancia viva.
//! Por eso usamos un singleton global que persiste durante toda la vida del proceso.

use arboard::Clipboard;
use std::sync::{Mutex, OnceLock};

/// Resultado de inicializacion del clipboard
type ClipboardResult = Result<Mutex<Clipboard>, String>;

/// Singleton global para mantener el clipboard vivo en Linux.
/// En X11/Wayland, cuando la instancia de Clipboard se destruye,
/// el contenido se vuelve inaccesible para otras aplicaciones.
static CLIPBOARD: OnceLock<ClipboardResult> = OnceLock::new();

/// Administrador de clipboard para copiar texto transcrito.
/// Usa un singleton interno para garantizar persistencia en Linux.
pub struct ClipboardManager;

impl ClipboardManager {
    /// Obtiene o inicializa la instancia singleton del clipboard
    fn instance() -> anyhow::Result<&'static Mutex<Clipboard>> {
        let result = CLIPBOARD.get_or_init(|| {
            match Clipboard::new() {
                Ok(clipboard) => {
                    log::info!("📋 Clipboard singleton inicializado");
                    Ok(Mutex::new(clipboard))
                }
                Err(e) => {
                    log::error!("❌ Error inicializando clipboard: {}", e);
                    Err(e.to_string())
                }
            }
        });

        match result {
            Ok(mutex) => Ok(mutex),
            Err(e) => Err(anyhow::anyhow!("Error inicializando clipboard: {}", e)),
        }
    }

    /// Crea un nuevo administrador de clipboard (para compatibilidad)
    pub fn new() -> anyhow::Result<Self> {
        // Inicializar el singleton si no existe
        Self::instance()?;
        Ok(Self)
    }

    /// Copia texto al clipboard
    pub fn set_text(&mut self, text: &str) -> anyhow::Result<()> {
        let clipboard = Self::instance()?;
        let mut guard = clipboard
            .lock()
            .map_err(|e| anyhow::anyhow!("Error obteniendo lock del clipboard: {}", e))?;

        guard
            .set_text(text)
            .map_err(|e| anyhow::anyhow!("Error copiando al clipboard: {}", e))?;

        log::info!("📋 Texto copiado al clipboard: {} caracteres", text.len());
        Ok(())
    }

    /// Lee texto del clipboard
    pub fn get_text(&mut self) -> anyhow::Result<String> {
        let clipboard = Self::instance()?;
        let mut guard = clipboard
            .lock()
            .map_err(|e| anyhow::anyhow!("Error obteniendo lock del clipboard: {}", e))?;

        guard
            .get_text()
            .map_err(|e| anyhow::anyhow!("Error leyendo clipboard: {}", e))
    }

    /// Limpia el clipboard
    pub fn clear(&mut self) -> anyhow::Result<()> {
        let clipboard = Self::instance()?;
        let mut guard = clipboard
            .lock()
            .map_err(|e| anyhow::anyhow!("Error obteniendo lock del clipboard: {}", e))?;

        guard
            .clear()
            .map_err(|e| anyhow::anyhow!("Error limpiando clipboard: {}", e))
    }
}

/// Copia texto al clipboard en una sola llamada (utility function).
/// Usa el singleton interno, seguro para Linux.
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

    #[test]
    #[ignore] // Ignorar en CI sin display
    fn test_clipboard_singleton_persistence() {
        // Primera escritura
        {
            let mut clipboard = ClipboardManager::new().expect("No se pudo inicializar clipboard");
            clipboard
                .set_text("Test persistencia")
                .expect("Error escribiendo");
        }
        // ClipboardManager se destruye aqui, pero el singleton sigue vivo

        // Segunda lectura - debe seguir funcionando
        {
            let mut clipboard = ClipboardManager::new().expect("No se pudo inicializar clipboard");
            let text = clipboard.get_text().expect("Error leyendo");
            assert_eq!(text, "Test persistencia");
        }
    }
}
