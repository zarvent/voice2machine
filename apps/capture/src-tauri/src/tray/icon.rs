//! Administrador de iconos de tray para diferentes estados.
//!
//! Actualiza el icono de la bandeja segun el estado de grabacion:
//! - Idle: Icono normal (microfono gris)
//! - Recording: Icono activo (microfono rojo/pulsante)
//! - Processing: Icono procesando (microfono con spinner)

use std::path::PathBuf;
use tauri::{
    image::Image,
    menu::{MenuBuilder, MenuItemBuilder},
    tray::{TrayIcon, TrayIconBuilder},
    AppHandle, Emitter, Manager,
};

use crate::config::RecordingState;

/// IDs para los iconos de tray segun estado
const TRAY_ICON_IDLE: &str = "tray-idle";
const TRAY_ICON_RECORDING: &str = "tray-recording";
const TRAY_ICON_PROCESSING: &str = "tray-processing";

/// Administrador del icono de tray
pub struct TrayManager {
    /// Handle del tray icon
    tray_id: String,
}

impl TrayManager {
    /// Crea y configura el tray icon para la aplicacion
    pub fn setup(app: &AppHandle) -> anyhow::Result<Self> {
        let tray_id = "main-tray".to_string();

        // Crear menu del tray
        let toggle_item = MenuItemBuilder::with_id("toggle", "Toggle Recording (Ctrl+Shift+Space)")
            .build(app)
            .map_err(|e| anyhow::anyhow!("Error creando menu item toggle: {}", e))?;

        let settings_item = MenuItemBuilder::with_id("settings", "Settings")
            .build(app)
            .map_err(|e| anyhow::anyhow!("Error creando menu item settings: {}", e))?;

        let quit_item = MenuItemBuilder::with_id("quit", "Quit")
            .build(app)
            .map_err(|e| anyhow::anyhow!("Error creando menu item quit: {}", e))?;

        let menu = MenuBuilder::new(app)
            .item(&toggle_item)
            .separator()
            .item(&settings_item)
            .separator()
            .item(&quit_item)
            .build()
            .map_err(|e| anyhow::anyhow!("Error construyendo menu: {}", e))?;

        // Cargar icono inicial (idle)
        let icon_path = get_icon_path(RecordingState::Idle);
        let icon = load_icon(&icon_path)?;

        // Crear tray icon
        let _tray = TrayIconBuilder::with_id(&tray_id)
            .icon(icon)
            .menu(&menu)
            .tooltip("Capture - Voice to Text")
            .on_menu_event(move |app, event| {
                handle_menu_event(app, &event.id().0);
            })
            .on_tray_icon_event(|tray, event| {
                if let tauri::tray::TrayIconEvent::Click { .. } = event {
                    // Click en el icono - toggle recording
                    let app = tray.app_handle();
                    if let Err(e) = emit_toggle_event(&app) {
                        log::error!("Error emitiendo evento toggle: {}", e);
                    }
                }
            })
            .build(app)
            .map_err(|e| anyhow::anyhow!("Error creando tray icon: {}", e))?;

        log::info!("Tray icon configurado correctamente");

        Ok(Self { tray_id })
    }

    /// Actualiza el icono segun el estado
    pub fn update_state(&self, app: &AppHandle, state: RecordingState) -> anyhow::Result<()> {
        let icon_path = get_icon_path(state);
        let icon = load_icon(&icon_path)?;

        // Obtener el tray icon existente
        if let Some(tray) = app.tray_by_id(&self.tray_id) {
            tray.set_icon(Some(icon))
                .map_err(|e| anyhow::anyhow!("Error actualizando icono: {}", e))?;

            // Actualizar tooltip segun estado
            let tooltip = match state {
                RecordingState::Idle => "Capture - Ready",
                RecordingState::Recording => "Capture - Recording...",
                RecordingState::Processing => "Capture - Processing...",
            };
            tray.set_tooltip(Some(tooltip))
                .map_err(|e| anyhow::anyhow!("Error actualizando tooltip: {}", e))?;
        }

        Ok(())
    }

    /// Retorna el ID del tray
    pub fn id(&self) -> &str {
        &self.tray_id
    }
}

/// Obtiene la ruta del icono segun el estado
fn get_icon_path(state: RecordingState) -> PathBuf {
    let icon_name = match state {
        RecordingState::Idle => "icon-idle.png",
        RecordingState::Recording => "icon-recording.png",
        RecordingState::Processing => "icon-processing.png",
    };

    // Los iconos estan en src-tauri/icons/
    PathBuf::from("icons").join(icon_name)
}

/// Carga un icono desde archivo o usa fallback embebido
fn load_icon(path: &PathBuf) -> anyhow::Result<Image<'static>> {
    // Intentar cargar desde archivo
    if path.exists() {
        // Leer el archivo de imagen y decodificarlo a RGBA
        let bytes = std::fs::read(path)
            .map_err(|e| anyhow::anyhow!("Error leyendo icono {:?}: {}", path, e))?;
        
        let img = image::load_from_memory(&bytes)
            .map_err(|e| anyhow::anyhow!("Error decodificando icono {:?}: {}", path, e))?;
        
        let rgba = img.to_rgba8();
        let (width, height) = rgba.dimensions();
        
        Ok(Image::new_owned(rgba.into_raw(), width, height))
    } else {
        // Usar icono embebido como fallback
        // Esto es un icono PNG simple de 32x32 pixeles (negro transparente)
        log::warn!("Icono {:?} no encontrado, usando fallback", path);
        create_fallback_icon()
    }
}

/// Crea un icono fallback simple (circulo de color)
fn create_fallback_icon() -> anyhow::Result<Image<'static>> {
    // Icono de 32x32 RGBA (4 bytes por pixel)
    // Crear un circulo simple
    let size = 32usize;
    let mut rgba = vec![0u8; size * size * 4];

    let center = size as f32 / 2.0;
    let radius = center - 2.0;

    for y in 0..size {
        for x in 0..size {
            let dx = x as f32 - center;
            let dy = y as f32 - center;
            let dist = (dx * dx + dy * dy).sqrt();

            let idx = (y * size + x) * 4;

            if dist <= radius {
                // Dentro del circulo - color gris oscuro
                rgba[idx] = 80;      // R
                rgba[idx + 1] = 80;  // G
                rgba[idx + 2] = 80;  // B
                rgba[idx + 3] = 255; // A
            } else if dist <= radius + 1.0 {
                // Borde suave (antialiasing)
                let alpha = ((radius + 1.0 - dist) * 255.0) as u8;
                rgba[idx] = 80;
                rgba[idx + 1] = 80;
                rgba[idx + 2] = 80;
                rgba[idx + 3] = alpha;
            }
            // Fuera del circulo: transparente (ya inicializado a 0)
        }
    }

    Ok(Image::new_owned(rgba, size as u32, size as u32))
}

/// Maneja eventos del menu de tray
fn handle_menu_event(app: &AppHandle, item_id: &str) {
    match item_id {
        "toggle" => {
            if let Err(e) = emit_toggle_event(app) {
                log::error!("Error emitiendo evento toggle: {}", e);
            }
        }
        "settings" => {
            // Mostrar ventana de settings
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }
        "quit" => {
            log::info!("Saliendo de la aplicacion...");
            app.exit(0);
        }
        _ => {
            log::warn!("Menu item desconocido: {}", item_id);
        }
    }
}

/// Emite evento para toggle de grabacion
fn emit_toggle_event(app: &AppHandle) -> anyhow::Result<()> {
    app.emit("toggle-recording", ())
        .map_err(|e| anyhow::anyhow!("Error emitiendo evento: {}", e))
}

/// Crea iconos de tray en diferentes colores para cada estado
pub mod icons {
    use super::*;

    /// Genera un icono de microfono simple
    /// color: RGB tuple
    pub fn generate_mic_icon(color: (u8, u8, u8)) -> anyhow::Result<Image<'static>> {
        let size = 32usize;
        let mut rgba = vec![0u8; size * size * 4];

        let (r, g, b) = color;

        // Dibujar forma de microfono simplificada
        // Cabeza del mic (circulo superior)
        draw_circle(&mut rgba, size, 16.0, 10.0, 6.0, r, g, b);
        
        // Cuerpo del mic (rectangulo)
        draw_rect(&mut rgba, size, 13, 10, 6, 12, r, g, b);
        
        // Base del mic (linea)
        draw_rect(&mut rgba, size, 10, 24, 12, 2, r, g, b);
        
        // Soporte (linea vertical)
        draw_rect(&mut rgba, size, 15, 22, 2, 4, r, g, b);

        Ok(Image::new_owned(rgba, size as u32, size as u32))
    }

    fn draw_circle(
        rgba: &mut [u8],
        size: usize,
        cx: f32,
        cy: f32,
        radius: f32,
        r: u8,
        g: u8,
        b: u8,
    ) {
        for y in 0..size {
            for x in 0..size {
                let dx = x as f32 - cx;
                let dy = y as f32 - cy;
                let dist = (dx * dx + dy * dy).sqrt();

                if dist <= radius {
                    let idx = (y * size + x) * 4;
                    rgba[idx] = r;
                    rgba[idx + 1] = g;
                    rgba[idx + 2] = b;
                    rgba[idx + 3] = 255;
                }
            }
        }
    }

    fn draw_rect(
        rgba: &mut [u8],
        size: usize,
        x: usize,
        y: usize,
        w: usize,
        h: usize,
        r: u8,
        g: u8,
        b: u8,
    ) {
        for dy in 0..h {
            for dx in 0..w {
                let px = x + dx;
                let py = y + dy;
                if px < size && py < size {
                    let idx = (py * size + px) * 4;
                    rgba[idx] = r;
                    rgba[idx + 1] = g;
                    rgba[idx + 2] = b;
                    rgba[idx + 3] = 255;
                }
            }
        }
    }

    /// Icono para estado idle (gris)
    pub fn idle_icon() -> anyhow::Result<Image<'static>> {
        generate_mic_icon((128, 128, 128))
    }

    /// Icono para estado recording (rojo)
    pub fn recording_icon() -> anyhow::Result<Image<'static>> {
        generate_mic_icon((220, 53, 69))
    }

    /// Icono para estado processing (amarillo/naranja)
    pub fn processing_icon() -> anyhow::Result<Image<'static>> {
        generate_mic_icon((255, 193, 7))
    }
}
