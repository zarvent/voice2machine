//! Máquina de estados para detección de segmentos de voz.
//!
//! Implementa debouncing para evitar falsos positivos y detectar
//! cuándo un segmento de voz ha terminado.

use crate::config::VadConfig;

/// Estados de la máquina de estados de VAD
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VadState {
    /// Esperando inicio de voz
    Idle,
    /// Voz detectada, confirmando (debounce para evitar falsos positivos)
    SpeechPending {
        /// Timestamp cuando se detectó voz por primera vez
        started_at_ms: u64,
    },
    /// Voz confirmada, grabando activamente
    SpeechActive,
    /// Silencio detectado, esperando confirmación para finalizar
    SilencePending {
        /// Timestamp cuando se detectó silencio
        started_at_ms: u64,
    },
}

impl Default for VadState {
    fn default() -> Self {
        Self::Idle
    }
}

/// Máquina de estados para detección de segmentos de voz
pub struct VadStateMachine {
    /// Estado actual
    state: VadState,
    /// Configuración de tiempos
    config: VadConfig,
    /// Tiempo actual en milisegundos
    current_time_ms: u64,
}

/// Eventos emitidos por la máquina de estados
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VadEvent {
    /// Sin cambio significativo
    None,
    /// Se confirmó el inicio de speech
    SpeechStarted,
    /// Se confirmó el fin de speech
    SpeechEnded,
    /// Se alcanzó el límite máximo de duración
    MaxDurationReached,
}

impl VadStateMachine {
    /// Crea una nueva máquina de estados
    pub fn new(config: VadConfig) -> Self {
        Self {
            state: VadState::Idle,
            config,
            current_time_ms: 0,
        }
    }

    /// Procesa un resultado de VAD y actualiza el estado
    ///
    /// # Arguments
    /// * `is_speech` - Si el chunk actual contiene voz
    /// * `chunk_duration_ms` - Duración del chunk en milisegundos
    ///
    /// # Returns
    /// * `VadEvent` indicando si hubo un cambio significativo
    pub fn process(&mut self, is_speech: bool, chunk_duration_ms: u64) -> VadEvent {
        self.current_time_ms += chunk_duration_ms;

        let (new_state, event) = match self.state {
            VadState::Idle => {
                if is_speech {
                    (
                        VadState::SpeechPending {
                            started_at_ms: self.current_time_ms,
                        },
                        VadEvent::None,
                    )
                } else {
                    (VadState::Idle, VadEvent::None)
                }
            }

            VadState::SpeechPending { started_at_ms } => {
                if is_speech {
                    let elapsed = self.current_time_ms - started_at_ms;
                    if elapsed >= self.config.min_speech_duration_ms {
                        // Voz confirmada
                        log::debug!(
                            "✅ Speech confirmado después de {}ms",
                            elapsed
                        );
                        (VadState::SpeechActive, VadEvent::SpeechStarted)
                    } else {
                        // Seguir esperando confirmación
                        (
                            VadState::SpeechPending { started_at_ms },
                            VadEvent::None,
                        )
                    }
                } else {
                    // Falso positivo, volver a idle
                    log::debug!("❌ Falso positivo detectado, volviendo a Idle");
                    (VadState::Idle, VadEvent::None)
                }
            }

            VadState::SpeechActive => {
                if is_speech {
                    (VadState::SpeechActive, VadEvent::None)
                } else {
                    // Posible fin de speech
                    (
                        VadState::SilencePending {
                            started_at_ms: self.current_time_ms,
                        },
                        VadEvent::None,
                    )
                }
            }

            VadState::SilencePending { started_at_ms } => {
                if is_speech {
                    // Silencio interrumpido, continuar speech
                    log::debug!("🔄 Silencio interrumpido, continuando speech");
                    (VadState::SpeechActive, VadEvent::None)
                } else {
                    let elapsed = self.current_time_ms - started_at_ms;
                    if elapsed >= self.config.min_silence_duration_ms {
                        // Silencio confirmado, fin de speech
                        log::debug!(
                            "✅ Silencio confirmado después de {}ms, finalizando speech",
                            elapsed
                        );
                        (VadState::Idle, VadEvent::SpeechEnded)
                    } else {
                        // Seguir esperando confirmación
                        (
                            VadState::SilencePending { started_at_ms },
                            VadEvent::None,
                        )
                    }
                }
            }
        };

        self.state = new_state;
        event
    }

    /// Verifica si estamos capturando speech activamente
    pub fn is_capturing(&self) -> bool {
        matches!(
            self.state,
            VadState::SpeechActive | VadState::SilencePending { .. }
        )
    }

    /// Retorna el estado actual
    pub fn state(&self) -> VadState {
        self.state
    }

    /// Resetea la máquina de estados
    pub fn reset(&mut self) {
        self.state = VadState::Idle;
        self.current_time_ms = 0;
    }

    /// Fuerza el fin del speech (ej: por límite de duración)
    pub fn force_end(&mut self) -> VadEvent {
        if self.is_capturing() {
            self.state = VadState::Idle;
            VadEvent::MaxDurationReached
        } else {
            VadEvent::None
        }
    }

    /// Retorna el tiempo transcurrido desde el inicio del speech actual
    pub fn speech_duration_ms(&self) -> Option<u64> {
        match self.state {
            VadState::SpeechActive | VadState::SilencePending { .. } => {
                // El tiempo desde que empezamos a capturar
                Some(self.current_time_ms)
            }
            _ => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_config() -> VadConfig {
        VadConfig {
            threshold: 0.35,
            min_speech_duration_ms: 100, // 100ms para tests rápidos
            min_silence_duration_ms: 200,
            speech_pad_ms: 50,
            energy_fallback_threshold: 0.005,
        }
    }

    #[test]
    fn test_idle_to_speech() {
        let mut sm = VadStateMachine::new(test_config());

        // Detectar voz
        let event = sm.process(true, 50);
        assert_eq!(event, VadEvent::None);
        assert!(matches!(sm.state(), VadState::SpeechPending { .. }));

        // Confirmar después de min_speech_duration
        let event = sm.process(true, 60);
        assert_eq!(event, VadEvent::SpeechStarted);
        assert_eq!(sm.state(), VadState::SpeechActive);
    }

    #[test]
    fn test_false_positive() {
        let mut sm = VadStateMachine::new(test_config());

        // Detectar voz brevemente
        sm.process(true, 50);
        assert!(matches!(sm.state(), VadState::SpeechPending { .. }));

        // Silencio antes de confirmar = falso positivo
        let event = sm.process(false, 30);
        assert_eq!(event, VadEvent::None);
        assert_eq!(sm.state(), VadState::Idle);
    }

    #[test]
    fn test_speech_to_silence() {
        let mut sm = VadStateMachine::new(test_config());

        // Ir a SpeechActive
        sm.process(true, 50);
        sm.process(true, 60);
        assert_eq!(sm.state(), VadState::SpeechActive);

        // Detectar silencio
        sm.process(false, 50);
        assert!(matches!(sm.state(), VadState::SilencePending { .. }));

        // Confirmar silencio
        let event = sm.process(false, 200);
        assert_eq!(event, VadEvent::SpeechEnded);
        assert_eq!(sm.state(), VadState::Idle);
    }

    #[test]
    fn test_interrupted_silence() {
        let mut sm = VadStateMachine::new(test_config());

        // Ir a SpeechActive
        sm.process(true, 50);
        sm.process(true, 60);

        // Silencio breve
        sm.process(false, 50);
        assert!(matches!(sm.state(), VadState::SilencePending { .. }));

        // Interrumpido por voz
        let event = sm.process(true, 30);
        assert_eq!(event, VadEvent::None);
        assert_eq!(sm.state(), VadState::SpeechActive);
    }

    #[test]
    fn test_is_capturing() {
        let mut sm = VadStateMachine::new(test_config());

        assert!(!sm.is_capturing());

        sm.process(true, 50);
        assert!(!sm.is_capturing()); // Pending no cuenta

        sm.process(true, 60);
        assert!(sm.is_capturing()); // Active sí

        sm.process(false, 50);
        assert!(sm.is_capturing()); // SilencePending también
    }
}
