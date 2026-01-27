//! Módulo de detección de actividad de voz (VAD).
//!
//! Utiliza Silero VAD para filtrar silencio antes de enviar audio a Whisper.
//! Incluye manejo de estado y buffering para detectar segmentos de voz completos.

pub mod buffer;
pub mod detector;
pub mod state_machine;

pub use buffer::*;
pub use detector::*;
pub use state_machine::*;
