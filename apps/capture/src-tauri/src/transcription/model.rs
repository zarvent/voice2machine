//! Descarga y gestión del modelo Whisper.
//!
//! Descarga el modelo large-v3-turbo desde HuggingFace si no existe localmente.

use futures_util::StreamExt;
use sha2::{Digest, Sha256};
use std::path::Path;
use tokio::fs::{self, File};
use tokio::io::AsyncWriteExt;

use crate::config::{
    get_model_path, get_models_dir, DownloadProgress, DownloadStatus, ModelInfo,
    MODEL_DOWNLOAD_URL, MODEL_EXPECTED_SIZE,
};

/// Verifica si el modelo existe y tiene un tamaño razonable
pub async fn check_model_exists() -> bool {
    let model_path = match get_model_path() {
        Ok(p) => p,
        Err(_) => return false,
    };

    if !model_path.exists() {
        return false;
    }

    // Verificar que el archivo tiene un tamaño razonable (al menos 1GB)
    match fs::metadata(&model_path).await {
        Ok(meta) => meta.len() > 1_000_000_000,
        Err(_) => false,
    }
}

/// Obtiene información del modelo
pub async fn get_model_info() -> anyhow::Result<ModelInfo> {
    let path = get_model_path()?;
    let exists = path.exists();

    let (size_bytes, verified) = if exists {
        let meta = fs::metadata(&path).await?;
        (meta.len(), meta.len() > 1_000_000_000)
    } else {
        (0, false)
    };

    Ok(ModelInfo {
        path,
        name: "ggml-large-v3-turbo".to_string(),
        size_bytes,
        verified,
    })
}

/// Callback para reportar progreso de descarga
pub type ProgressCallback = Box<dyn Fn(DownloadProgress) + Send + 'static>;

/// Descarga el modelo con reporte de progreso
pub async fn download_model(progress_callback: Option<ProgressCallback>) -> anyhow::Result<()> {
    let models_dir = get_models_dir()?;
    let model_path = get_model_path()?;

    // Crear directorio de modelos si no existe
    fs::create_dir_all(&models_dir).await?;

    log::info!("📥 Iniciando descarga del modelo desde {}", MODEL_DOWNLOAD_URL);

    // Reportar estado inicial
    if let Some(ref cb) = progress_callback {
        cb(DownloadProgress {
            downloaded: 0,
            total: MODEL_EXPECTED_SIZE,
            percentage: 0.0,
            status: DownloadStatus::Preparing,
        });
    }

    // Crear cliente HTTP
    let client = reqwest::Client::new();
    let response = client
        .get(MODEL_DOWNLOAD_URL)
        .send()
        .await
        .map_err(|e| anyhow::anyhow!("Error conectando: {}", e))?;

    if !response.status().is_success() {
        return Err(anyhow::anyhow!(
            "Error HTTP {}: {}",
            response.status(),
            response.status().canonical_reason().unwrap_or("Unknown")
        ));
    }

    let total_size = response
        .content_length()
        .unwrap_or(MODEL_EXPECTED_SIZE);

    // Archivo temporal para descarga
    let temp_path = model_path.with_extension("bin.tmp");
    let mut file = File::create(&temp_path).await?;
    let mut downloaded: u64 = 0;
    let mut hasher = Sha256::new();

    // Reportar inicio de descarga
    if let Some(ref cb) = progress_callback {
        cb(DownloadProgress {
            downloaded: 0,
            total: total_size,
            percentage: 0.0,
            status: DownloadStatus::Downloading,
        });
    }

    // Descargar en chunks
    let mut stream = response.bytes_stream();
    while let Some(chunk_result) = stream.next().await {
        let chunk = chunk_result.map_err(|e| anyhow::anyhow!("Error descargando: {}", e))?;

        file.write_all(&chunk).await?;
        hasher.update(&chunk);
        downloaded += chunk.len() as u64;

        // Reportar progreso cada ~1MB
        if let Some(ref cb) = progress_callback {
            let percentage = (downloaded as f32 / total_size as f32) * 100.0;
            cb(DownloadProgress {
                downloaded,
                total: total_size,
                percentage,
                status: DownloadStatus::Downloading,
            });
        }
    }

    file.flush().await?;
    drop(file);

    log::info!("📥 Descarga completada: {} bytes", downloaded);

    // Reportar verificación
    if let Some(ref cb) = progress_callback {
        cb(DownloadProgress {
            downloaded,
            total: total_size,
            percentage: 100.0,
            status: DownloadStatus::Verifying,
        });
    }

    // Calcular hash (para futuro uso)
    let hash = hasher.finalize();
    log::info!("🔐 SHA256: {:x}", hash);

    // Mover archivo temporal a ubicación final
    fs::rename(&temp_path, &model_path).await?;

    // Reportar completado
    if let Some(ref cb) = progress_callback {
        cb(DownloadProgress {
            downloaded,
            total: total_size,
            percentage: 100.0,
            status: DownloadStatus::Completed,
        });
    }

    log::info!("✅ Modelo guardado en {:?}", model_path);

    Ok(())
}

/// Elimina el modelo descargado
pub async fn delete_model() -> anyhow::Result<()> {
    let model_path = get_model_path()?;
    if model_path.exists() {
        fs::remove_file(&model_path).await?;
        log::info!("🗑️ Modelo eliminado");
    }
    Ok(())
}

/// Verifica la integridad del modelo existente
pub async fn verify_model(path: &Path) -> anyhow::Result<bool> {
    if !path.exists() {
        return Ok(false);
    }

    let meta = fs::metadata(path).await?;

    // Verificación básica: tamaño mínimo esperado
    if meta.len() < 1_000_000_000 {
        log::warn!("⚠️ Modelo demasiado pequeño: {} bytes", meta.len());
        return Ok(false);
    }

    // TODO: Verificar hash SHA256 contra valor conocido
    // Por ahora solo verificamos tamaño

    Ok(true)
}

/// Descargador de modelos con interfaz simplificada
pub struct ModelDownloader;

impl ModelDownloader {
    /// Crea un nuevo descargador
    pub fn new() -> Self {
        Self
    }

    /// Descarga el modelo con callback de progreso
    pub async fn download_with_progress<F>(&self, callback: F) -> anyhow::Result<()>
    where
        F: Fn(DownloadProgress) + Send + 'static,
    {
        download_model(Some(Box::new(callback))).await
    }

    /// Descarga el modelo sin callback
    pub async fn download(&self) -> anyhow::Result<()> {
        download_model(None).await
    }

    /// Verifica si el modelo existe
    pub async fn exists(&self) -> bool {
        check_model_exists().await
    }

    /// Obtiene información del modelo
    pub async fn info(&self) -> anyhow::Result<ModelInfo> {
        get_model_info().await
    }
}

impl Default for ModelDownloader {
    fn default() -> Self {
        Self::new()
    }
}
