//! Capture - Utilidad de voz a texto de alto rendimiento.
//!
//! Punto de entrada principal de la aplicacion Tauri.

// Previene ventana de consola en Windows para builds de release
#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use capture::{
    audio, config,
    config::{AppConfig, AudioDeviceInfo, DownloadProgress},
    setup_app, transcription::ModelDownloader, AppState,
};
use tauri::Emitter;

// ============================================================================
// Comandos IPC para Tauri
// ============================================================================

/// Alterna el estado de grabacion
#[tauri::command]
async fn toggle_recording(
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
async fn get_state(
    state: tauri::State<'_, AppState>,
) -> Result<config::RecordingState, String> {
    let pipeline = state.pipeline.lock().await;
    Ok(pipeline.state())
}

/// Lista los dispositivos de audio disponibles
#[tauri::command]
async fn list_audio_devices() -> Result<Vec<AudioDeviceInfo>, String> {
    audio::list_input_devices().map_err(|e| e.to_string())
}

/// Obtiene la configuracion actual
#[tauri::command]
async fn get_config(
    state: tauri::State<'_, AppState>,
) -> Result<AppConfig, String> {
    let config = state.config.lock().await;
    Ok(config.clone())
}

/// Actualiza la configuracion
#[tauri::command]
async fn set_config(
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
async fn is_model_downloaded() -> Result<bool, String> {
    let model_path = config::get_model_path().map_err(|e| e.to_string())?;
    Ok(model_path.exists())
}

/// Obtiene informacion del modelo
#[tauri::command]
async fn get_model_info() -> Result<Option<config::ModelInfo>, String> {
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
async fn download_model(
    app: tauri::AppHandle,
) -> Result<(), String> {
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
async fn cancel_download() -> Result<(), String> {
    // TODO: Implementar cancelacion
    log::warn!("Cancelacion de descarga no implementada");
    Ok(())
}

/// Carga el modelo de Whisper
#[tauri::command]
async fn load_model(
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
async fn is_model_loaded(
    state: tauri::State<'_, AppState>,
) -> Result<bool, String> {
    let pipeline = state.pipeline.lock().await;
    Ok(pipeline.is_model_loaded())
}

// ============================================================================
// Main
// ============================================================================

fn main() {
    // Inicializar logger
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info"))
        .format_timestamp_millis()
        .init();

    log::info!("Iniciando Capture v{}", env!("CARGO_PKG_VERSION"));

    // Construir y ejecutar aplicacion Tauri
    tauri::Builder::default()
        // Estado compartido
        .manage(AppState::new())
        // Plugins
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_notification::init())
        // Comandos IPC
        .invoke_handler(tauri::generate_handler![
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
        ])
        // Setup
        .setup(|app| {
            setup_app(app)?;
            Ok(())
        })
        // Ejecutar
        .run(tauri::generate_context!())
        .expect("Error ejecutando aplicacion Tauri");
}
