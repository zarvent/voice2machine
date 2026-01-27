//! Wrapper de whisper-rs para transcripción de audio.
//!
//! Proporciona una interfaz simple para transcribir audio usando el modelo Whisper.

use std::path::Path;
use std::sync::Arc;
use tokio::sync::Mutex;
use whisper_rs::{FullParams, SamplingStrategy, WhisperContext, WhisperContextParameters};

/// Transcriptor de audio usando Whisper
pub struct WhisperTranscriber {
    /// Contexto de Whisper (thread-safe)
    context: Arc<Mutex<WhisperContext>>,
    /// Idioma configurado
    language: String,
    /// Número de threads para transcripción
    n_threads: i32,
}

impl WhisperTranscriber {
    /// Crea un nuevo transcriptor cargando el modelo especificado
    ///
    /// # Arguments
    /// * `model_path` - Ruta al archivo del modelo (.bin)
    /// * `language` - Código de idioma ("es" o "en")
    pub fn new(model_path: &Path, language: &str) -> anyhow::Result<Self> {
        log::info!("🧠 Cargando modelo Whisper desde {:?}...", model_path);

        let params = WhisperContextParameters::default();

        let context = WhisperContext::new_with_params(
            model_path
                .to_str()
                .ok_or_else(|| anyhow::anyhow!("Ruta de modelo inválida"))?,
            params,
        )
        .map_err(|e| anyhow::anyhow!("Error cargando modelo Whisper: {:?}", e))?;

        log::info!("✅ Modelo Whisper cargado exitosamente");

        Ok(Self {
            context: Arc::new(Mutex::new(context)),
            language: language.to_string(),
            n_threads: 4,
        })
    }

    /// Transcribe audio a texto
    ///
    /// # Arguments
    /// * `audio` - Samples de audio en formato f32, 16kHz, mono
    ///
    /// # Returns
    /// * Texto transcrito
    pub async fn transcribe(&self, audio: &[f32]) -> anyhow::Result<String> {
        if audio.is_empty() {
            return Ok(String::new());
        }

        let audio = audio.to_vec();
        let language = self.language.clone();
        let n_threads = self.n_threads;
        let context = self.context.clone();

        // Ejecutar transcripción en thread bloqueante
        let result = tokio::task::spawn_blocking(move || {
            let ctx = context.blocking_lock();

            // Crear estado para esta transcripción
            let mut state = ctx
                .create_state()
                .map_err(|e| anyhow::anyhow!("Error creando estado: {:?}", e))?;

            // Configurar parámetros
            let mut params = FullParams::new(SamplingStrategy::Greedy { best_of: 1 });

            // Configuración de idioma
            params.set_language(Some(&language));

            // Optimizaciones para velocidad
            params.set_n_threads(n_threads);
            params.set_translate(false);
            params.set_no_timestamps(true);

            // CRÍTICO: Bajar no_speech_threshold para evitar doble filtrado con VAD
            // El diagnóstico mostró que 0.6 era muy agresivo
            params.set_no_speech_thold(0.4);

            // Suprimir tokens no útiles
            params.set_suppress_blank(true);
            params.set_suppress_nst(true);

            // Ejecutar transcripción
            state
                .full(params, &audio)
                .map_err(|e| anyhow::anyhow!("Error en transcripción: {:?}", e))?;

            // Recolectar resultados
            let num_segments = state
                .full_n_segments()
                .map_err(|e| anyhow::anyhow!("Error obteniendo segmentos: {:?}", e))?;

            let mut result = String::new();
            for i in 0..num_segments {
                if let Ok(segment) = state.full_get_segment_text(i) {
                    result.push_str(&segment);
                    result.push(' ');
                }
            }

            Ok::<String, anyhow::Error>(result.trim().to_string())
        })
        .await
        .map_err(|e| anyhow::anyhow!("Error en task de transcripción: {}", e))??;

        Ok(result)
    }

    /// Cambia el idioma de transcripción
    pub fn set_language(&mut self, language: &str) {
        self.language = language.to_string();
        log::info!("🌐 Idioma cambiado a: {}", language);
    }

    /// Retorna el idioma actual
    pub fn language(&self) -> &str {
        &self.language
    }

    /// Configura el número de threads
    pub fn set_threads(&mut self, threads: i32) {
        self.n_threads = threads.max(1);
    }
}

/// Resultado de una transcripción
#[derive(Debug, Clone)]
pub struct TranscriptionResult {
    /// Texto transcrito
    pub text: String,
    /// Duración del audio procesado en segundos
    pub audio_duration_s: f32,
    /// Tiempo de procesamiento en milisegundos
    pub processing_time_ms: u64,
}

impl TranscriptionResult {
    /// Crea un nuevo resultado de transcripción
    pub fn new(text: String, audio_duration_s: f32, processing_time_ms: u64) -> Self {
        Self {
            text,
            audio_duration_s,
            processing_time_ms,
        }
    }

    /// Retorna el ratio de tiempo real (< 1.0 significa más rápido que tiempo real)
    pub fn real_time_ratio(&self) -> f32 {
        if self.audio_duration_s > 0.0 {
            (self.processing_time_ms as f32 / 1000.0) / self.audio_duration_s
        } else {
            0.0
        }
    }
}
