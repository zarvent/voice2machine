//! Detector de actividad de voz usando Silero VAD.
//!
//! Wrapper sobre voice_activity_detector que proporciona una interfaz simple
//! para detectar si un chunk de audio contiene voz.

use voice_activity_detector::VoiceActivityDetector;

use crate::config::VadConfig;

/// Detector de actividad de voz
pub struct VadDetector {
    /// Detector de Silero VAD
    detector: VoiceActivityDetector,
    /// Configuración de VAD
    config: VadConfig,
}

impl VadDetector {
    /// Crea un nuevo detector de VAD
    ///
    /// # Arguments
    /// * `sample_rate` - Sample rate del audio (debe ser 16000 para Silero)
    /// * `config` - Configuración de umbrales y tiempos
    pub fn new(sample_rate: u32, config: VadConfig) -> anyhow::Result<Self> {
        // Silero VAD requiere chunks de 512 samples a 16kHz (~32ms)
        let chunk_size = 512usize;

        let detector = VoiceActivityDetector::builder()
            .sample_rate(sample_rate)
            .chunk_size(chunk_size)
            .build()
            .map_err(|e| anyhow::anyhow!("Error inicializando VAD: {}", e))?;

        log::info!(
            "🎯 VAD inicializado: {}Hz, chunk_size={}, threshold={}",
            sample_rate,
            chunk_size,
            config.threshold
        );

        Ok(Self { detector, config })
    }

    /// Predice si un chunk de audio contiene voz
    ///
    /// # Arguments
    /// * `samples` - Samples de audio en formato f32 (16kHz mono)
    ///
    /// # Returns
    /// * `VadResult` con la probabilidad y si se considera voz
    pub fn predict(&mut self, samples: &[f32]) -> VadResult {
        // Si el chunk es muy pequeño, usar fallback de energía
        if samples.len() < 512 {
            return self.predict_energy(samples);
        }

        // Convertir a i16 que es lo que espera voice_activity_detector
        let samples_i16: Vec<i16> = samples
            .iter()
            .map(|&s| (s.clamp(-1.0, 1.0) * 32767.0) as i16)
            .collect();

        let probability = self.detector.predict(samples_i16);
        let is_speech = probability > self.config.threshold;

        VadResult {
            probability,
            is_speech,
            method: VadMethod::Silero,
        }
    }

    /// Fallback usando detección por energía (RMS)
    /// Se usa cuando el chunk es demasiado pequeño para Silero
    fn predict_energy(&self, samples: &[f32]) -> VadResult {
        if samples.is_empty() {
            return VadResult {
                probability: 0.0,
                is_speech: false,
                method: VadMethod::Energy,
            };
        }

        // Calcular RMS (Root Mean Square)
        let sum_squares: f32 = samples.iter().map(|s| s * s).sum();
        let rms = (sum_squares / samples.len() as f32).sqrt();

        // Convertir RMS a probabilidad aproximada (0-1)
        // RMS típico para voz es ~0.05-0.3
        let probability = (rms / 0.15).clamp(0.0, 1.0);
        let is_speech = rms > self.config.energy_fallback_threshold;

        VadResult {
            probability,
            is_speech,
            method: VadMethod::Energy,
        }
    }

    /// Resetea el estado interno del detector
    pub fn reset(&mut self) {
        self.detector.reset();
    }

    /// Retorna la configuración actual
    pub fn config(&self) -> &VadConfig {
        &self.config
    }

    /// Actualiza el umbral de detección
    pub fn set_threshold(&mut self, threshold: f32) {
        self.config.threshold = threshold.clamp(0.0, 1.0);
    }
}

/// Resultado de la detección de VAD
#[derive(Debug, Clone, Copy)]
pub struct VadResult {
    /// Probabilidad de voz (0.0 - 1.0)
    pub probability: f32,
    /// Si se considera voz según el umbral
    pub is_speech: bool,
    /// Método usado para la detección
    pub method: VadMethod,
}

/// Método de detección utilizado
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VadMethod {
    /// Silero VAD (modelo de IA)
    Silero,
    /// Detección por energía (fallback)
    Energy,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vad_creation() {
        let config = VadConfig::default();
        let result = VadDetector::new(16000, config);
        assert!(result.is_ok());
    }

    #[test]
    fn test_energy_fallback() {
        let config = VadConfig::default();
        let detector = VadDetector::new(16000, config).unwrap();

        // Silencio
        let silence = vec![0.0f32; 100];
        let result = detector.predict_energy(&silence);
        assert!(!result.is_speech);
        assert_eq!(result.method, VadMethod::Energy);

        // Ruido fuerte
        let noise: Vec<f32> = (0..100).map(|i| (i as f32 * 0.1).sin() * 0.5).collect();
        let result = detector.predict_energy(&noise);
        assert!(result.is_speech);
    }
}
