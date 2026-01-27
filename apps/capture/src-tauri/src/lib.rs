//! Capture - Utilidad de voz a texto de alto rendimiento.
//!
//! Biblioteca principal que expone los modulos de la aplicacion
//! y los comandos IPC para Tauri.

pub mod audio;
pub mod config;
pub mod output;
pub mod pipeline;
pub mod transcription;
pub mod tray;
pub mod vad;

use std::sync::Arc;
use tokio::sync::Mutex;

use config::{AppConfig, AudioDeviceInfo, DownloadProgress, RecordingState};
use pipeline::{Pipeline, PipelineConfig, PipelineEvent};
use transcription::ModelDownloader;
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
// Comandos IPC para Tauri
// ============================================================================

/// Alterna el estado de grabacion
#[tauri::command]
pub async fn toggle_recording(
    state: tauri::State<'_, AppState>,
) -> Result<bool, String> {
    let mut pipeline = state.pipeline.lock().await;
    pipeline
        .toggle_recording()
        .await
        .map_err(|e| e.to_string())
}

/// Obtiene el estado actual de grabacion
#[tauri::command]
pub async fn get_state(
    state: tauri::State<'_, AppState>,
) -> Result<RecordingState, String> {
    let pipeline = state.pipeline.lock().await;
    Ok(pipeline.state())
}

/// Lista los dispositivos de audio disponibles
#[tauri::command]
pub async fn list_audio_devices() -> Result<Vec<AudioDeviceInfo>, String> {
    audio::list_input_devices().map_err(|e| e.to_string())
}

/// Obtiene la configuracion actual
#[tauri::command]
pub async fn get_config(
    state: tauri::State<'_, AppState>,
) -> Result<AppConfig, String> {
    let config = state.config.lock().await;
    Ok(config.clone())
}

/// Actualiza la configuracion
#[tauri::command]
pub async fn set_config(
    state: tauri::State<'_, AppState>,
    new_config: AppConfig,
) -> Result<(), String> {
    // Actualizar config
    {
        let mut config = state.config.lock().await;
        *config = new_config.clone();
    }

    // Actualizar pipeline
    {
        let mut pipeline = state.pipeline.lock().await;
        pipeline.update_config(new_config);
    }

    log::info!("Configuracion actualizada");
    Ok(())
}

/// Verifica si el modelo esta descargado
#[tauri::command]
pub async fn is_model_downloaded() -> Result<bool, String> {
    let model_path = config::get_model_path().map_err(|e| e.to_string())?;
    Ok(model_path.exists())
}

/// Obtiene informacion del modelo
#[tauri::command]
pub async fn get_model_info() -> Result<Option<config::ModelInfo>, String> {
    let model_path = config::get_model_path().map_err(|e| e.to_string())?;
    
    if !model_path.exists() {
        return Ok(None);
    }

    let metadata = std::fs::metadata(&model_path).map_err(|e| e.to_string())?;

    Ok(Some(config::ModelInfo {
        path: model_path,
        name: "ggml-large-v3-turbo".to_string(),
        size_bytes: metadata.len(),
        verified: true,
    }))
}

/// Inicia la descarga del modelo
/// Emite eventos de progreso via tauri events
#[tauri::command]
pub async fn download_model(
    app: tauri::AppHandle,
) -> Result<(), String> {
    use tauri::Emitter;

    let downloader = ModelDownloader::new();

    // Callback para progreso
    let app_clone = app.clone();
    let progress_callback = move |progress: DownloadProgress| {
        let _ = app_clone.emit("download-progress", progress);
    };

    downloader
        .download_with_progress(progress_callback)
        .await
        .map_err(|e| e.to_string())?;

    // Emitir evento de completado
    let _ = app.emit("download-complete", ());

    Ok(())
}

/// Cancela una descarga en progreso
#[tauri::command]
pub async fn cancel_download() -> Result<(), String> {
    // TODO: Implementar cancelacion
    log::warn!("Cancelacion de descarga no implementada");
    Ok(())
}

/// Carga el modelo de Whisper
#[tauri::command]
pub async fn load_model(
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    let mut pipeline = state.pipeline.lock().await;
    pipeline
        .ensure_model_loaded()
        .await
        .map_err(|e| e.to_string())
}

/// Verifica si el modelo esta cargado en memoria
#[tauri::command]
pub async fn is_model_loaded(
    state: tauri::State<'_, AppState>,
) -> Result<bool, String> {
    let pipeline = state.pipeline.lock().await;
    Ok(pipeline.is_model_loaded())
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

    // Escuchar eventos del pipeline para actualizar tray
    let app_handle_events = app_handle.clone();
    tauri::async_runtime::spawn(async move {
        // Este loop escuchara eventos del pipeline cuando se implemente
        // Por ahora, el tray se actualiza directamente desde los comandos
        log::debug!("Event listener iniciado");
    });

    Ok(())
}

/// Genera los handlers de comandos para Tauri
pub fn get_invoke_handler() -> impl Fn(tauri::ipc::Invoke) -> bool + Send + Sync + 'static {
    tauri::generate_handler![
        toggle_recording,
        get_state,
        list_audio_devices,
        get_config,
        set_config,
        is_model_downloaded,
        get_model_info,
        download_model,
        cancel_download,
        load_model,
        is_model_loaded,
    ]
}
