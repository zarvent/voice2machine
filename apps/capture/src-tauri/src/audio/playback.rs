//! Reproducción de sonidos de feedback.
//!
//! Usa rodio para reproducir archivos WAV embebidos en el binario.
//! Los sonidos proporcionan feedback auditivo inmediato al usuario.

use rodio::{Decoder, OutputStream, Sink};
use std::io::Cursor;
use std::thread;

// Sonidos embebidos en el binario para evitar dependencia de archivos externos
// Los archivos WAV deben estar en src-tauri/sounds/
const START_SOUND: &[u8] = include_bytes!("../../sounds/start.wav");
const STOP_SOUND: &[u8] = include_bytes!("../../sounds/stop.wav");
const SUCCESS_SOUND: &[u8] = include_bytes!("../../sounds/success.wav");
const ERROR_SOUND: &[u8] = include_bytes!("../../sounds/error.wav");

/// Tipos de sonidos de feedback disponibles
#[derive(Debug, Clone, Copy)]
pub enum SoundCue {
    /// Sonido al iniciar grabación (bip ascendente)
    Start,
    /// Sonido al detener grabación (click mecánico)
    Stop,
    /// Sonido de éxito al copiar al clipboard (campanilla sutil)
    Success,
    /// Sonido de error (tono descendente)
    Error,
}

impl SoundCue {
    /// Obtiene los bytes del sonido correspondiente
    fn get_bytes(&self) -> &'static [u8] {
        match self {
            SoundCue::Start => START_SOUND,
            SoundCue::Stop => STOP_SOUND,
            SoundCue::Success => SUCCESS_SOUND,
            SoundCue::Error => ERROR_SOUND,
        }
    }
}

/// Reproduce un sonido de feedback de forma no bloqueante
///
/// El sonido se reproduce en un thread separado para no bloquear la ejecución principal.
/// Si la reproducción falla (ej: sin dispositivo de audio), el error se registra pero
/// no se propaga - los sonidos son opcionales.
pub fn play_sound(cue: SoundCue) {
    let bytes = cue.get_bytes();

    // Reproducción no bloqueante en thread separado
    thread::spawn(move || {
        if let Err(e) = play_sound_blocking(bytes) {
            log::warn!("⚠️ Error reproduciendo sonido {:?}: {}", cue, e);
        }
    });
}

/// Reproduce un sonido de forma bloqueante
fn play_sound_blocking(bytes: &'static [u8]) -> anyhow::Result<()> {
    let (_stream, stream_handle) = OutputStream::try_default()
        .map_err(|e| anyhow::anyhow!("Error abriendo dispositivo de audio: {}", e))?;

    let source = Decoder::new(Cursor::new(bytes))
        .map_err(|e| anyhow::anyhow!("Error decodificando WAV: {}", e))?;

    let sink = Sink::try_new(&stream_handle)
        .map_err(|e| anyhow::anyhow!("Error creando sink: {}", e))?;

    sink.append(source);
    sink.sleep_until_end();

    Ok(())
}

/// Reproduce un sonido solo si los sonidos están habilitados
pub fn play_sound_if_enabled(cue: SoundCue, sound_enabled: bool) {
    if sound_enabled {
        play_sound(cue);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sound_bytes_exist() {
        // Verificar que los sonidos están embebidos
        assert!(!START_SOUND.is_empty());
        assert!(!STOP_SOUND.is_empty());
        assert!(!SUCCESS_SOUND.is_empty());
        assert!(!ERROR_SOUND.is_empty());
    }

    #[test]
    fn test_get_bytes() {
        assert_eq!(SoundCue::Start.get_bytes().as_ptr(), START_SOUND.as_ptr());
        assert_eq!(SoundCue::Stop.get_bytes().as_ptr(), STOP_SOUND.as_ptr());
    }
}
