//! Definición del esquema de configuración y funciones de acceso.
//!
//! Utiliza serde para serialización y tauri-plugin-store para persistencia.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Configuración principal de la aplicación
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    /// ID del dispositivo de audio seleccionado (None = default del sistema)
    pub audio_device_id: Option<String>,

    /// Shortcut global para iniciar/detener grabación
    pub shortcut: String,

    /// Idioma para transcripción ("es" o "en")
    pub language: String,

    /// Habilitar sonidos de feedback
    pub sound_enabled: bool,

    /// Configuración de VAD
    pub vad: VadConfig,
}

/// Configuración del detector de actividad de voz
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VadConfig {
    /// Umbral de probabilidad para detectar voz (0.0-1.0)
    /// Valor más bajo = más sensible, puede capturar más ruido
    /// Valor más alto = menos sensible, puede perder voz suave
    pub threshold: f32,

    /// Duración mínima de voz para confirmar speech (ms)
    pub min_speech_duration_ms: u64,

    /// Duración de silencio para finalizar grabación (ms)
    pub min_silence_duration_ms: u64,

    /// Padding de audio antes/después del speech (ms)
    pub speech_pad_ms: u64,

    /// Umbral de energía para fallback cuando VAD no tiene suficientes samples
    pub energy_fallback_threshold: f32,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            audio_device_id: None,
            shortcut: "Ctrl+Shift+Space".to_string(),
            language: "es".to_string(),
            sound_enabled: true,
            vad: VadConfig::default(),
        }
    }
}

impl Default for VadConfig {
    fn default() -> Self {
        Self {
            // Umbral más bajo que el problemático 0.4 del diagnóstico
            threshold: 0.35,
            min_speech_duration_ms: 150,
            // Más rápido que 1000ms para mejor responsividad
            min_silence_duration_ms: 800,
            speech_pad_ms: 300,
            // Más bajo que el problemático 0.01 del diagnóstico
            energy_fallback_threshold: 0.005,
        }
    }
}

/// Información de un dispositivo de audio
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioDeviceInfo {
    /// ID único del dispositivo
    pub id: String,
    /// Nombre legible del dispositivo
    pub name: String,
    /// Es el dispositivo por defecto del sistema
    pub is_default: bool,
}

/// Estado de grabación de la aplicación
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum RecordingState {
    /// Sin actividad, esperando shortcut
    Idle,
    /// Grabando audio del micrófono
    Recording,
    /// Procesando audio con Whisper
    Processing,
}

impl Default for RecordingState {
    fn default() -> Self {
        Self::Idle
    }
}

/// Información sobre el modelo de transcripción
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelInfo {
    /// Ruta al archivo del modelo
    pub path: PathBuf,
    /// Nombre del modelo
    pub name: String,
    /// Tamaño en bytes
    pub size_bytes: u64,
    /// Si el modelo existe y está verificado
    pub verified: bool,
}

/// Progreso de descarga del modelo
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DownloadProgress {
    /// Bytes descargados
    pub downloaded: u64,
    /// Total de bytes a descargar
    pub total: u64,
    /// Porcentaje completado (0-100)
    pub percentage: f32,
    /// Estado de la descarga
    pub status: DownloadStatus,
}

/// Estado de la descarga
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum DownloadStatus {
    /// Preparando descarga
    Preparing,
    /// Descargando
    Downloading,
    /// Verificando integridad
    Verifying,
    /// Completado exitosamente
    Completed,
    /// Error en la descarga
    Failed,
}

/// Obtiene la ruta del directorio de datos de la aplicación
pub fn get_app_data_dir() -> anyhow::Result<PathBuf> {
    dirs::data_dir()
        .map(|p| p.join("capture"))
        .ok_or_else(|| anyhow::anyhow!("No se pudo determinar el directorio de datos"))
}

/// Obtiene la ruta del directorio de modelos
pub fn get_models_dir() -> anyhow::Result<PathBuf> {
    Ok(get_app_data_dir()?.join("models"))
}

/// Obtiene la ruta completa al modelo large-v3-turbo
pub fn get_model_path() -> anyhow::Result<PathBuf> {
    Ok(get_models_dir()?.join("ggml-large-v3-turbo.bin"))
}

/// URL de descarga del modelo
pub const MODEL_DOWNLOAD_URL: &str =
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin";

/// Tamaño esperado del modelo (aproximado para validación)
pub const MODEL_EXPECTED_SIZE: u64 = 1_550_000_000; // ~1.5GB

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = AppConfig::default();
        assert_eq!(config.shortcut, "Ctrl+Shift+Space");
        assert_eq!(config.language, "es");
        assert!(config.sound_enabled);
        assert_eq!(config.vad.threshold, 0.35);
    }

    #[test]
    fn test_recording_state_serialization() {
        let state = RecordingState::Recording;
        let json = serde_json::to_string(&state).unwrap();
        assert_eq!(json, "\"recording\"");
    }
}
