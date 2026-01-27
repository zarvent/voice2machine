//! Buffer de audio para pre-speech y acumulación de segmentos de voz.
//!
//! Utiliza ring buffers para mantener audio reciente sin consumir memoria infinita.

use ringbuffer::{AllocRingBuffer, RingBuffer};

/// Buffer de audio para captura de voz
pub struct SpeechBuffer {
    /// Buffer circular para pre-speech (captura inicio de palabras)
    pre_speech: AllocRingBuffer<f32>,
    /// Buffer dinámico para speech activo
    speech: Vec<f32>,
    /// Duración del pre-buffer en samples (mantenido para debugging)
    #[allow(dead_code)]
    pre_speech_samples: usize,
    /// Máximo de samples a acumular
    max_speech_samples: usize,
    /// Sample rate para cálculos de duración
    sample_rate: u32,
}

impl SpeechBuffer {
    /// Crea un nuevo buffer de speech
    ///
    /// # Arguments
    /// * `sample_rate` - Sample rate del audio (típicamente 16000)
    /// * `pre_speech_duration_ms` - Duración del pre-buffer en ms
    /// * `max_speech_duration_s` - Duración máxima de speech en segundos
    pub fn new(sample_rate: u32, pre_speech_duration_ms: u64, max_speech_duration_s: f32) -> Self {
        let pre_speech_samples = (sample_rate as f64 * pre_speech_duration_ms as f64 / 1000.0) as usize;
        let max_speech_samples = (sample_rate as f32 * max_speech_duration_s) as usize;

        log::debug!(
            "📦 SpeechBuffer: pre_speech={}samples ({}ms), max={}samples ({}s)",
            pre_speech_samples,
            pre_speech_duration_ms,
            max_speech_samples,
            max_speech_duration_s
        );

        Self {
            pre_speech: AllocRingBuffer::new(pre_speech_samples.max(1)),
            speech: Vec::with_capacity(max_speech_samples),
            pre_speech_samples,
            max_speech_samples,
            sample_rate,
        }
    }

    /// Agrega samples al pre-buffer (siempre activo, antes de detectar speech)
    pub fn push_pre_speech(&mut self, samples: &[f32]) {
        self.pre_speech.extend(samples.iter().copied());
    }

    /// Inicia la captura de speech (incluye el pre-buffer)
    /// Llamar cuando VAD detecta inicio de voz
    pub fn start_speech(&mut self) {
        self.speech.clear();
        // Incluir el pre-buffer para no cortar el inicio de las palabras
        self.speech.extend(self.pre_speech.iter().copied());
        log::debug!(
            "🎤 Speech iniciado con {} samples de pre-buffer",
            self.speech.len()
        );
    }

    /// Agrega samples durante speech activo
    pub fn push_speech(&mut self, samples: &[f32]) {
        let remaining = self.max_speech_samples.saturating_sub(self.speech.len());
        if remaining > 0 {
            let to_add = samples.len().min(remaining);
            self.speech.extend(samples.iter().take(to_add).copied());
        }
    }

    /// Finaliza y retorna el audio de speech acumulado
    pub fn end_speech(&mut self) -> Vec<f32> {
        let speech = std::mem::take(&mut self.speech);
        log::debug!(
            "🎤 Speech finalizado: {} samples ({:.2}s)",
            speech.len(),
            speech.len() as f32 / self.sample_rate as f32
        );
        speech
    }

    /// Verifica si se alcanzó el límite máximo de speech
    pub fn is_at_capacity(&self) -> bool {
        self.speech.len() >= self.max_speech_samples
    }

    /// Retorna la duración actual del speech en milisegundos
    pub fn speech_duration_ms(&self) -> u64 {
        (self.speech.len() as f64 * 1000.0 / self.sample_rate as f64) as u64
    }

    /// Retorna el número de samples acumulados
    pub fn speech_len(&self) -> usize {
        self.speech.len()
    }

    /// Limpia todos los buffers
    pub fn clear(&mut self) {
        self.pre_speech.clear();
        self.speech.clear();
    }

    /// Verifica si hay speech acumulado
    pub fn has_speech(&self) -> bool {
        !self.speech.is_empty()
    }
}

impl Default for SpeechBuffer {
    fn default() -> Self {
        // 500ms pre-buffer, 30s máximo
        Self::new(16000, 500, 30.0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pre_speech_buffer() {
        let mut buffer = SpeechBuffer::new(16000, 500, 30.0);

        // Agregar audio al pre-buffer
        let audio: Vec<f32> = (0..8000).map(|i| (i as f32 / 8000.0)).collect();
        buffer.push_pre_speech(&audio);

        // Iniciar speech - debe incluir pre-buffer
        buffer.start_speech();
        assert!(buffer.speech_len() > 0);
    }

    #[test]
    fn test_max_capacity() {
        let mut buffer = SpeechBuffer::new(16000, 100, 1.0); // 1 segundo máximo

        buffer.start_speech();

        // Agregar más de 1 segundo
        let audio = vec![0.5f32; 20000]; // 1.25 segundos
        buffer.push_speech(&audio);

        // Debe estar en capacidad máxima
        assert!(buffer.is_at_capacity());
        assert_eq!(buffer.speech_len(), 16000); // Exactamente 1 segundo
    }

    #[test]
    fn test_end_speech() {
        let mut buffer = SpeechBuffer::default();
        buffer.start_speech();
        buffer.push_speech(&[0.1, 0.2, 0.3]);

        let speech = buffer.end_speech();
        assert!(speech.len() >= 3);

        // Después de end_speech, el buffer debe estar vacío
        assert!(!buffer.has_speech());
    }
}
