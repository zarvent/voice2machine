//! Capture - Utilidad de voz a texto de alto rendimiento.
//!
//! Punto de entrada principal de la aplicacion Tauri.

// Previene ventana de consola en Windows para builds de release
#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use capture::{setup_app, get_invoke_handler, AppState};

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
        .invoke_handler(get_invoke_handler())
        // Setup
        .setup(|app| {
            setup_app(app)?;
            Ok(())
        })
        // Ejecutar
        .run(tauri::generate_context!())
        .expect("Error ejecutando aplicacion Tauri");
}
