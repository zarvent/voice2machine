//! Resampling de audio a formato Whisper (16kHz mono).
//!
//! Utiliza rubato para conversión de alta calidad con bajo overhead.

use rubato::{
    Resampler, SincFixedIn, SincInterpolationParameters, SincInterpolationType, WindowFunction,
};

use super::AudioChunk;

/// Sample rate requerido por Whisper
pub const WHISPER_SAMPLE_RATE: u32 = 16_000;

/// Número de canales requerido por Whisper
pub const WHISPER_CHANNELS: u16 = 1;

/// Resampler de audio para convertir a formato Whisper
pub struct AudioResampler {
    /// Resampler de rubato (solo se crea si es necesario resamplear)
    resampler: Option<SincFixedIn<f32>>,
    /// Sample rate de entrada
    input_sample_rate: u32,
    /// Número de canales de entrada
    input_channels: u16,
    /// Ratio de conversión
    ratio: f64,
}

impl AudioResampler {
    /// Crea un nuevo resampler para el formato de entrada especificado
    pub fn new(input_sample_rate: u32, input_channels: u16) -> anyhow::Result<Self> {
        let ratio = WHISPER_SAMPLE_RATE as f64 / input_sample_rate as f64;
        
        // Solo crear resampler si es necesario
        let resampler = if input_sample_rate != WHISPER_SAMPLE_RATE {
            // Parámetros optimizados para voz (menor latencia, buena calidad)
            let params = SincInterpolationParameters {
                sinc_len: 64,           // Balance entre calidad y latencia
                f_cutoff: 0.95,
                interpolation: SincInterpolationType::Linear, // Rápido, suficiente para voz
                oversampling_factor: 128,
                window: WindowFunction::BlackmanHarris2,
            };

            // Tamaño de chunk típico (~10ms de audio @ 48kHz = 480 samples)
            let chunk_size = (input_sample_rate as f64 * 0.01) as usize;
            
            let resampler = SincFixedIn::<f32>::new(
                ratio,
                2.0, // Max ratio adjustment
                params,
                chunk_size.max(64), // Mínimo 64 samples
                input_channels as usize,
            )
            .map_err(|e| anyhow::anyhow!("Error creando resampler: {}", e))?;

            Some(resampler)
        } else {
            None
        };

        log::info!(
            "🔄 Resampler configurado: {}Hz {}ch -> {}Hz mono (ratio: {:.4})",
            input_sample_rate,
            input_channels,
            WHISPER_SAMPLE_RATE,
            ratio
        );

        Ok(Self {
            resampler,
            input_sample_rate,
            input_channels,
            ratio,
        })
    }

    /// Procesa un chunk de audio y lo convierte a formato Whisper (16kHz mono f32)
    pub fn process(&mut self, chunk: &AudioChunk) -> anyhow::Result<Vec<f32>> {
        // Paso 1: Convertir a mono si es necesario
        let mono_samples = self.to_mono(&chunk.samples);

        // Paso 2: Resamplear si es necesario
        let resampled = self.resample(&mono_samples)?;

        Ok(resampled)
    }

    /// Convierte audio multicanal a mono promediando canales
    fn to_mono(&self, samples: &[f32]) -> Vec<f32> {
        if self.input_channels == 1 {
            return samples.to_vec();
        }

        let channels = self.input_channels as usize;
        samples
            .chunks(channels)
            .map(|chunk| {
                let sum: f32 = chunk.iter().sum();
                sum / channels as f32
            })
            .collect()
    }

    /// Resamplea audio a 16kHz usando rubato
    fn resample(&mut self, mono_samples: &[f32]) -> anyhow::Result<Vec<f32>> {
        // Si no hay resampler, el audio ya está a 16kHz
        let Some(resampler) = &mut self.resampler else {
            return Ok(mono_samples.to_vec());
        };

        // rubato espera Vec<Vec<f32>> donde cada Vec interno es un canal
        let input = vec![mono_samples.to_vec()];
        
        // Calcular tamaño de salida aproximado
        let output_len = (mono_samples.len() as f64 * self.ratio).ceil() as usize + 10;
        let mut output = vec![vec![0.0f32; output_len]];

        // Procesar el audio
        let (_, output_frames) = resampler
            .process_into_buffer(&input, &mut output, None)
            .map_err(|e| anyhow::anyhow!("Error en resampling: {}", e))?;

        // Extraer solo los frames válidos
        output[0].truncate(output_frames);
        
        Ok(output.into_iter().next().unwrap_or_default())
    }

    /// Retorna el sample rate de entrada configurado
    pub fn input_sample_rate(&self) -> u32 {
        self.input_sample_rate
    }

    /// Retorna el número de canales de entrada configurado
    pub fn input_channels(&self) -> u16 {
        self.input_channels
    }
}

/// Convierte audio a formato Whisper en una sola llamada (utility function)
pub fn convert_to_whisper_format(
    samples: &[f32],
    source_sample_rate: u32,
    source_channels: u16,
) -> anyhow::Result<Vec<f32>> {
    let mut resampler = AudioResampler::new(source_sample_rate, source_channels)?;
    let chunk = AudioChunk {
        samples: samples.to_vec(),
        sample_rate: source_sample_rate,
        channels: source_channels,
    };
    resampler.process(&chunk)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mono_conversion() {
        let resampler = AudioResampler::new(16000, 2).unwrap();
        
        // Stereo: L=1.0, R=0.0, L=0.5, R=0.5
        let stereo = vec![1.0, 0.0, 0.5, 0.5];
        let mono = resampler.to_mono(&stereo);
        
        // Promedio: (1.0+0.0)/2=0.5, (0.5+0.5)/2=0.5
        assert_eq!(mono.len(), 2);
        assert!((mono[0] - 0.5).abs() < 0.001);
        assert!((mono[1] - 0.5).abs() < 0.001);
    }

    #[test]
    fn test_no_resample_needed() {
        let resampler = AudioResampler::new(16000, 1).unwrap();
        assert!(resampler.resampler.is_none());
    }

    #[test]
    fn test_resample_needed() {
        let resampler = AudioResampler::new(48000, 2).unwrap();
        assert!(resampler.resampler.is_some());
    }
}
