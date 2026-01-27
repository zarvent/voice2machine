//! Módulo de audio para captura y procesamiento.
//!
//! Contiene funcionalidades para:
//! - Enumerar y seleccionar dispositivos de entrada
//! - Capturar audio del micrófono
//! - Resamplear audio a 16kHz mono (formato Whisper)
//! - Reproducir sonidos de feedback

pub mod capture;
pub mod devices;
pub mod playback;
pub mod resampler;

pub use capture::*;
pub use devices::*;
pub use playback::*;
pub use resampler::*;
