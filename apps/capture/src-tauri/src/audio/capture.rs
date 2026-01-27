//! Captura de audio del micrófono.
//!
//! Implementa un stream de entrada usando cpal con buffering via crossbeam channels.
//! El audio capturado se envía a través de canales para procesamiento asíncrono.

use cpal::traits::{DeviceTrait, StreamTrait};
use cpal::{Sample, SampleFormat, StreamConfig};
use crossbeam_channel::{bounded, Receiver, Sender};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use super::devices::select_input_device;

/// Chunk de audio capturado del micrófono
#[derive(Debug, Clone)]
pub struct AudioChunk {
    /// Samples de audio en formato f32
    pub samples: Vec<f32>,
    /// Sample rate original del dispositivo
    pub sample_rate: u32,
    /// Número de canales
    pub channels: u16,
}

/// Configuración para la captura de audio
#[derive(Debug, Clone)]
pub struct CaptureConfig {
    /// ID del dispositivo (None = default)
    pub device_id: Option<String>,
    /// Tamaño del buffer del canal (número de chunks)
    pub buffer_size: usize,
}

impl Default for CaptureConfig {
    fn default() -> Self {
        Self {
            device_id: None,
            // Buffer para ~2-4 segundos de audio dependiendo del chunk size
            buffer_size: 64,
        }
    }
}

/// Handle para controlar la captura de audio
pub struct AudioCapture {
    /// Receiver para obtener chunks de audio
    pub receiver: Receiver<AudioChunk>,
    /// Flag para indicar si la captura está activa
    running: Arc<AtomicBool>,
    /// Stream de audio (mantener vivo mientras se captura)
    _stream: cpal::Stream,
    /// Sample rate del dispositivo
    pub sample_rate: u32,
    /// Número de canales del dispositivo
    pub channels: u16,
}

impl AudioCapture {
    /// Inicia la captura de audio con la configuración especificada
    pub fn start(config: CaptureConfig) -> anyhow::Result<Self> {
        let device = select_input_device(config.device_id.as_deref())?;
        let supported_config = device
            .default_input_config()
            .map_err(|e| anyhow::anyhow!("Error obteniendo config del dispositivo: {}", e))?;

        let sample_rate = supported_config.sample_rate().0;
        let channels = supported_config.channels();
        let sample_format = supported_config.sample_format();

        let stream_config: StreamConfig = supported_config.into();

        // Canal bounded para backpressure - evita consumo de memoria infinito
        let (tx, rx) = bounded::<AudioChunk>(config.buffer_size);
        let running = Arc::new(AtomicBool::new(true));

        let stream = build_input_stream(
            &device,
            &stream_config,
            sample_format,
            tx,
            sample_rate,
            channels,
            running.clone(),
        )?;

        stream
            .play()
            .map_err(|e| anyhow::anyhow!("Error iniciando stream de audio: {}", e))?;

        log::info!(
            "🎤 Captura de audio iniciada: {}Hz, {} canales",
            sample_rate,
            channels
        );

        Ok(Self {
            receiver: rx,
            running,
            _stream: stream,
            sample_rate,
            channels,
        })
    }

    /// Verifica si la captura sigue activa
    pub fn is_running(&self) -> bool {
        self.running.load(Ordering::Relaxed)
    }

    /// Detiene la captura de audio
    pub fn stop(&self) {
        self.running.store(false, Ordering::Relaxed);
        log::info!("🎤 Captura de audio detenida");
    }
}

impl Drop for AudioCapture {
    fn drop(&mut self) {
        self.stop();
    }
}

/// Construye el stream de entrada según el formato del dispositivo
fn build_input_stream(
    device: &cpal::Device,
    config: &StreamConfig,
    sample_format: SampleFormat,
    tx: Sender<AudioChunk>,
    sample_rate: u32,
    channels: u16,
    running: Arc<AtomicBool>,
) -> anyhow::Result<cpal::Stream> {
    let stream = match sample_format {
        SampleFormat::F32 => build_stream::<f32>(device, config, tx, sample_rate, channels, running),
        SampleFormat::I16 => build_stream::<i16>(device, config, tx, sample_rate, channels, running),
        SampleFormat::U16 => build_stream::<u16>(device, config, tx, sample_rate, channels, running),
        _ => Err(anyhow::anyhow!(
            "Formato de sample no soportado: {:?}",
            sample_format
        )),
    }?;

    Ok(stream)
}

/// Construye el stream con conversión al tipo específico
fn build_stream<T>(
    device: &cpal::Device,
    config: &StreamConfig,
    tx: Sender<AudioChunk>,
    sample_rate: u32,
    channels: u16,
    running: Arc<AtomicBool>,
) -> anyhow::Result<cpal::Stream>
where
    T: cpal::SizedSample + cpal::FromSample<f32> + Send + 'static,
    f32: cpal::FromSample<T>,
{
    let stream = device
        .build_input_stream(
            config,
            move |data: &[T], _: &cpal::InputCallbackInfo| {
                if !running.load(Ordering::Relaxed) {
                    return;
                }

                // Convertir samples a f32
                let samples: Vec<f32> = data.iter().map(|&s| f32::from_sample(s)).collect();

                let chunk = AudioChunk {
                    samples,
                    sample_rate,
                    channels,
                };

                // try_send para no bloquear el callback de audio (crítico para latencia)
                if tx.try_send(chunk).is_err() {
                    // Buffer lleno - el consumidor es demasiado lento
                    // En producción, esto indica un problema de rendimiento
                    log::warn!("⚠️ Buffer de audio lleno, descartando chunk");
                }
            },
            |err| {
                log::error!("❌ Error en stream de audio: {}", err);
            },
            None, // Sin timeout
        )
        .map_err(|e| anyhow::anyhow!("Error creando stream de entrada: {}", e))?;

    Ok(stream)
}
