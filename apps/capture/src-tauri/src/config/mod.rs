//! Módulo de configuración de la aplicación.
//!
//! Maneja la persistencia de configuraciones del usuario usando tauri-plugin-store.
//! Almacena configuraciones como dispositivo de audio, idioma, shortcut, etc.

pub mod settings;

pub use settings::*;
