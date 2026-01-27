//! Modulo de pipeline de procesamiento de audio.
//!
//! Orquesta el flujo completo: audio -> VAD -> transcripcion -> clipboard

pub mod orchestrator;

pub use orchestrator::*;
