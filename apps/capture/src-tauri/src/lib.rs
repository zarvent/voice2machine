//! Capture - Utilidad de voz a texto de alto rendimiento.
//!
//! Biblioteca principal que expone los modulos de la aplicacion
//! y los tipos compartidos para Tauri.

pub mod audio;
pub mod config;
pub mod output;
pub mod pipeline;
pub mod transcription;
pub mod tray;
pub mod vad;

use std::sync::Arc;
use tokio::sync::Mutex;

use config::AppConfig;
use pipeline::{Pipeline, PipelineConfig};
use tray::TrayManager;

/// Estado global de la aplicacion compartido entre comandos
pub struct AppState {
    /// Pipeline de procesamiento
    pub pipeline: Arc<Mutex<Pipeline>>,
    /// Configuracion actual
    pub config: Arc<Mutex<AppConfig>>,
    /// Administrador de tray (opcional, se inicializa despues)
    pub tray_manager: Arc<Mutex<Option<TrayManager>>>,
}

impl AppState {
    /// Crea un nuevo estado de aplicacion
    pub fn new() -> Self {
        let config = AppConfig::default();
        let pipeline_config = PipelineConfig {
            app_config: config.clone(),
            max_recording_duration_s: 30.0,
        };

        Self {
            pipeline: Arc::new(Mutex::new(Pipeline::new(pipeline_config))),
            config: Arc::new(Mutex::new(config)),
            tray_manager: Arc::new(Mutex::new(None)),
        }
    }
}

impl Default for AppState {
    fn default() -> Self {
        Self::new()
    }
}

// ============================================================================
// Setup de la aplicacion
// ============================================================================

/// Configura los plugins y shortcuts de Tauri
pub fn setup_app(app: &mut tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    use tauri::{Emitter, Manager};
    use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, ShortcutState};

    let app_handle = app.handle().clone();

    // Configurar tray icon
    let state = app.state::<AppState>();
    {
        let tray_manager = TrayManager::setup(&app_handle)?;
        let mut tray_lock = state.tray_manager.blocking_lock();
        *tray_lock = Some(tray_manager);
    }

    // Registrar shortcut global
    let shortcut: Shortcut = "Ctrl+Shift+Space"
        .parse()
        .expect("Shortcut invalido");

    app.handle().plugin(
        tauri_plugin_global_shortcut::Builder::new()
            .with_handler(move |_app, shortcut_pressed, event| {
                if event.state() == ShortcutState::Pressed {
                    log::info!("Shortcut presionado: {:?}", shortcut_pressed);
                    // Emitir evento para toggle
                    if let Err(e) = _app.emit("toggle-recording", ()) {
                        log::error!("Error emitiendo evento: {}", e);
                    }
                }
            })
            .build(),
    )?;

    // Registrar el shortcut
    app.global_shortcut().register(shortcut)?;

    log::info!("Shortcut global registrado: Ctrl+Shift+Space");

    // Verificar si el modelo existe y mostrar ventana si es necesario
    let check_app_handle = app_handle.clone();
    tauri::async_runtime::spawn(async move {
        use crate::transcription::ModelDownloader;
        
        let downloader = ModelDownloader::new();
        if !downloader.exists().await {
            log::info!("Modelo no encontrado. Mostrando ventana de configuración.");
            if let Some(window) = check_app_handle.get_webview_window("main") {
                if let Err(e) = window.show() {
                    log::error!("Error mostrando ventana: {}", e);
                }
                if let Err(e) = window.set_focus() {
                    log::error!("Error dando foco a ventana: {}", e);
                }
            }
        }
    });

    // Escuchar eventos del pipeline para actualizar tray
    let _app_handle_events = app_handle.clone();
    tauri::async_runtime::spawn(async move {
        // Este loop escuchara eventos del pipeline cuando se implemente
        // Por ahora, el tray se actualiza directamente desde los comandos
        log::debug!("Event listener iniciado");
    });

    Ok(())
}
