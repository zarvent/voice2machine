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

use config::{AppConfig, RecordingState};
use pipeline::{Pipeline, PipelineConfig, PipelineEvent};
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
    use tauri::{Listener, Manager};
    use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, ShortcutState};

    let app_handle = app.handle().clone();

    // Configurar tray icon
    let state = app.state::<AppState>();
    {
        let tray_manager = TrayManager::setup(&app_handle)?;
        let mut tray_lock = state.tray_manager.blocking_lock();
        *tray_lock = Some(tray_manager);
    }

    // Configurar el AppHandle en el Pipeline para emision de eventos
    {
        let mut pipeline_lock = state.pipeline.blocking_lock();
        pipeline_lock.set_app_handle(app_handle.clone());
    }

    // Registrar shortcut global
    let shortcut: Shortcut = "Ctrl+Shift+Space"
        .parse()
        .expect("Shortcut invalido");

    // Clonar el handle para usar dentro del handler
    let shortcut_app_handle = app_handle.clone();

    app.handle().plugin(
        tauri_plugin_global_shortcut::Builder::new()
            .with_handler(move |_app, shortcut_pressed, event| {
                if event.state() == ShortcutState::Pressed {
                    log::info!("Shortcut presionado: {:?}", shortcut_pressed);

                    // Llamar toggle_recording DIRECTAMENTE en lugar de emitir evento
                    // Esto elimina la doble invocación que ocurría cuando el frontend
                    // escuchaba el evento y llamaba de vuelta via IPC
                    let app_handle = shortcut_app_handle.clone();
                    tauri::async_runtime::spawn(async move {
                        let state = app_handle.state::<AppState>();
                        let mut pipeline = state.pipeline.lock().await;
                        if let Err(e) = pipeline.toggle_recording().await {
                            log::error!("Error en toggle_recording: {}", e);
                        }
                    });
                }
            })
            .build(),
    )?;

    // Registrar el shortcut
    app.global_shortcut().register(shortcut)?;

    log::info!("Shortcut global registrado: Ctrl+Shift+Space");

    // Mostrar ventana si el modelo no existe, o siempre en modo debug
    let check_app_handle = app_handle.clone();
    tauri::async_runtime::spawn(async move {
        use crate::transcription::ModelDownloader;

        let downloader = ModelDownloader::new();
        let model_exists = downloader.exists().await;

        // En debug, siempre mostrar ventana para testing
        // En release, solo si el modelo no existe
        let should_show = if cfg!(debug_assertions) {
            log::info!("Modo debug: mostrando ventana de configuración");
            true
        } else if !model_exists {
            log::info!("Modelo no encontrado. Mostrando ventana de configuración.");
            true
        } else {
            false
        };

        if should_show {
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

    // Escuchar eventos del pipeline para actualizar tray icon
    let tray_app_handle = app_handle.clone();
    app_handle.listen("pipeline-event", move |event| {
        // Deserializar el evento
        if let Ok(pipeline_event) = serde_json::from_str::<PipelineEvent>(event.payload()) {
            // Solo actualizamos el tray en eventos de cambio de estado
            if let PipelineEvent::StateChanged { state: new_state } = pipeline_event {
                update_tray_for_state(&tray_app_handle, new_state);
            }
        }
    });

    log::info!("Event listener para tray icon configurado");

    Ok(())
}

/// Actualiza el icono del tray segun el estado del pipeline
fn update_tray_for_state(app_handle: &tauri::AppHandle, new_state: RecordingState) {
    use tauri::Manager;

    let app_state = app_handle.state::<AppState>();
    let tray_manager = app_state.tray_manager.clone();
    let app_handle = app_handle.clone();

    tauri::async_runtime::spawn(async move {
        if let Some(tray) = tray_manager.lock().await.as_ref() {
            if let Err(e) = tray.update_state(&app_handle, new_state) {
                log::error!("Error actualizando tray icon: {}", e);
            } else {
                log::debug!("Tray icon actualizado a estado: {:?}", new_state);
            }
        }
    });
}
