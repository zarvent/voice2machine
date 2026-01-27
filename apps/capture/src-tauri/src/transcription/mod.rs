//! Módulo de transcripción de voz a texto.
//!
//! Maneja la descarga del modelo Whisper y la transcripción de audio.

pub mod model;
pub mod whisper;

pub use model::*;
pub use whisper::*;
