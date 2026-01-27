//! Orquestador del pipeline de transcripcion.
//!
//! Conecta todos los componentes: captura de audio, VAD, buffer de speech,
//! transcripcion con Whisper, y salida al clipboard.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Instant;
use tokio::sync::{mpsc, Mutex as TokioMutex};

use crate::audio::{play_sound_if_enabled, AudioCapture, AudioResampler, CaptureConfig, SoundCue};
use crate::config::{AppConfig, RecordingState};
use crate::output::ClipboardManager;
use crate::transcription::WhisperTranscriber;
use crate::vad::{SpeechBuffer, VadDetector, VadEvent, VadStateMachine};

/// Eventos emitidos por el pipeline para actualizar la UI
#[derive(Debug, Clone)]
pub enum PipelineEvent {
    /// El estado de grabacion cambio
    StateChanged(RecordingState),
    /// Speech detectado, comenzando captura
    SpeechStarted,
    /// Speech finalizado, procesando
    SpeechEnded { duration_ms: u64 },
    /// Transcripcion completada exitosamente
    TranscriptionComplete {
        text: String,
        audio_duration_s: f32,
        processing_time_ms: u64,
    },
    /// Texto copiado al clipboard
    CopiedToClipboard { text: String },
    /// Error durante el pipeline
    Error { message: String },
}

/// Configuracion del pipeline
#[derive(Debug, Clone)]
pub struct PipelineConfig {
    /// Configuracion de la aplicacion
    pub app_config: AppConfig,
    /// Duracion maxima de grabacion en segundos
    pub max_recording_duration_s: f32,
}

impl Default for PipelineConfig {
    fn default() -> Self {
        Self {
            app_config: AppConfig::default(),
            max_recording_duration_s: 30.0,
        }
    }
}

/// Resultado de la fase de captura de audio
enum CaptureResult {
    /// Audio capturado exitosamente
    Success {
        audio: Vec<f32>,
        duration_s: f32,
    },
    /// Cancelado por el usuario
    Cancelled,
    /// No se detecto speech suficiente
    NoSpeech,
}

/// Orquestador del pipeline de transcripcion
pub struct Pipeline {
    /// Transmisor de eventos
    event_tx: mpsc::UnboundedSender<PipelineEvent>,
    /// Receptor de eventos (para la UI)
    event_rx: Option<mpsc::UnboundedReceiver<PipelineEvent>>,
    /// Estado actual
    state: Arc<std::sync::Mutex<RecordingState>>,
    /// Flag para cancelar grabacion
    cancel_flag: Arc<AtomicBool>,
    /// Transcriptor de Whisper (lazy-loaded, compartido con Arc)
    transcriber: Arc<TokioMutex<Option<WhisperTranscriber>>>,
    /// Configuracion
    config: Arc<std::sync::Mutex<PipelineConfig>>,
}

impl Pipeline {
    /// Crea un nuevo pipeline
    pub fn new(config: PipelineConfig) -> Self {
        let (event_tx, event_rx) = mpsc::unbounded_channel();
        
        Self {
            event_tx,
            event_rx: Some(event_rx),
            state: Arc::new(std::sync::Mutex::new(RecordingState::Idle)),
            cancel_flag: Arc::new(AtomicBool::new(false)),
            transcriber: Arc::new(TokioMutex::new(None)),
            config: Arc::new(std::sync::Mutex::new(config)),
        }
    }

    /// Toma el receptor de eventos (solo se puede llamar una vez)
    pub fn take_event_receiver(&mut self) -> Option<mpsc::UnboundedReceiver<PipelineEvent>> {
        self.event_rx.take()
    }

    /// Carga el modelo de Whisper si no esta cargado
    pub async fn ensure_model_loaded(&mut self) -> anyhow::Result<()> {
        let mut transcriber_lock = self.transcriber.lock().await;
        
        if transcriber_lock.is_some() {
            return Ok(());
        }

        let model_path = crate::config::get_model_path()?;
        if !model_path.exists() {
            return Err(anyhow::anyhow!(
                "Modelo no encontrado. Ejecuta la descarga primero."
            ));
        }

        let language = {
            let config = self.config.lock().unwrap();
            config.app_config.language.clone()
        };
        
        let transcriber = WhisperTranscriber::new(&model_path, &language)?;
        *transcriber_lock = Some(transcriber);

        log::info!("Modelo Whisper cargado exitosamente");
        Ok(())
    }

    /// Verifica si el modelo esta cargado
    pub fn is_model_loaded(&self) -> bool {
        // Para verificacion sincronica, usamos try_lock
        self.transcriber
            .try_lock()
            .map(|guard| guard.is_some())
            .unwrap_or(false)
    }

    /// Actualiza la configuracion
    pub fn update_config(&mut self, new_config: AppConfig) {
        let mut config = self.config.lock().unwrap();
        config.app_config = new_config.clone();
        
        // Actualizar idioma del transcriptor si esta cargado
        // Esto se hara en el proximo uso del transcriptor
    }

    /// Retorna el estado actual
    pub fn state(&self) -> RecordingState {
        *self.state.lock().unwrap()
    }

    fn set_state(&self, new_state: RecordingState) {
        *self.state.lock().unwrap() = new_state;
        let _ = self.event_tx.send(PipelineEvent::StateChanged(new_state));
    }

    /// Alterna el estado de grabacion (toggle)
    /// Retorna true si inicio grabacion, false si la cancelo
    pub async fn toggle_recording(&mut self) -> anyhow::Result<bool> {
        let current_state = self.state();

        match current_state {
            RecordingState::Idle => {
                self.start_recording().await?;
                Ok(true)
            }
            RecordingState::Recording => {
                self.cancel_recording();
                Ok(false)
            }
            RecordingState::Processing => {
                // No se puede cancelar durante procesamiento
                log::warn!("No se puede cancelar durante procesamiento");
                Ok(false)
            }
        }
    }

    /// Inicia la grabacion de audio
    async fn start_recording(&mut self) -> anyhow::Result<()> {
        // Verificar que el modelo este cargado
        self.ensure_model_loaded().await?;

        self.cancel_flag.store(false, Ordering::SeqCst);
        self.set_state(RecordingState::Recording);

        // Obtener configuracion
        let config = {
            let cfg = self.config.lock().unwrap();
            cfg.clone()
        };

        // Sonido de inicio
        play_sound_if_enabled(SoundCue::Start, config.app_config.sound_enabled);

        // Clonar recursos compartidos para el task
        let state = self.state.clone();
        let cancel_flag = self.cancel_flag.clone();
        let event_tx = self.event_tx.clone();
        let transcriber = self.transcriber.clone();
        let config_arc = self.config.clone();

        // Ejecutar pipeline en task separado
        tokio::spawn(async move {
            if let Err(e) = run_recording_pipeline(
                config_arc,
                state,
                cancel_flag,
                event_tx.clone(),
                transcriber,
            )
            .await
            {
                log::error!("Error en pipeline: {}", e);
                let _ = event_tx.send(PipelineEvent::Error {
                    message: e.to_string(),
                });
            }
        });

        Ok(())
    }

    /// Cancela la grabacion actual
    pub fn cancel_recording(&self) {
        self.cancel_flag.store(true, Ordering::SeqCst);
        log::info!("Grabacion cancelada por usuario");
    }
}

/// Ejecuta la fase de captura de audio (sincrona, no-Send)
/// 
/// Esta funcion corre en un spawn_blocking porque AudioCapture no es Send
fn run_audio_capture(
    config: PipelineConfig,
    cancel_flag: Arc<AtomicBool>,
    event_tx: mpsc::UnboundedSender<PipelineEvent>,
) -> anyhow::Result<CaptureResult> {
    // 1. Iniciar captura de audio
    let capture_config = CaptureConfig {
        device_id: config.app_config.audio_device_id.clone(),
        ..Default::default()
    };
    let capture = AudioCapture::start(capture_config)?;
    
    // 2. Crear resampler
    let mut resampler = AudioResampler::new(capture.sample_rate, capture.channels)?;

    // 3. Crear detector VAD
    let vad_config = config.app_config.vad.clone();
    let mut vad = VadDetector::new(16000, vad_config.clone())?;

    // 4. Crear maquina de estados VAD
    let mut vad_state = VadStateMachine::new(vad_config.clone());

    // 5. Crear buffer de speech
    let mut speech_buffer = SpeechBuffer::new(
        16000,
        vad_config.speech_pad_ms,
        config.max_recording_duration_s,
    );

    let mut speech_started = false;
    let recording_start = Instant::now();

    // Loop principal de captura
    loop {
        // Verificar cancelacion
        if cancel_flag.load(Ordering::Relaxed) {
            capture.stop();
            return Ok(CaptureResult::Cancelled);
        }

        // Verificar timeout maximo
        if recording_start.elapsed().as_secs_f32() > config.max_recording_duration_s + 5.0 {
            log::warn!("Timeout de grabacion alcanzado");
            break;
        }

        // Recibir chunk de audio (con timeout)
        let chunk = match capture.receiver.recv_timeout(std::time::Duration::from_millis(100)) {
            Ok(chunk) => chunk,
            Err(crossbeam_channel::RecvTimeoutError::Timeout) => continue,
            Err(crossbeam_channel::RecvTimeoutError::Disconnected) => {
                log::warn!("Canal de audio desconectado");
                break;
            }
        };

        // Resamplear a 16kHz mono
        let resampled = resampler.process(&chunk)?;

        // Calcular duracion del chunk en ms
        let chunk_duration_ms = (resampled.len() as f64 * 1000.0 / 16000.0) as u64;

        // Siempre agregar al pre-buffer
        speech_buffer.push_pre_speech(&resampled);

        // Detectar voz
        let vad_result = vad.predict(&resampled);

        // Procesar en maquina de estados
        let event = vad_state.process(vad_result.is_speech, chunk_duration_ms);

        match event {
            VadEvent::SpeechStarted => {
                log::info!("Speech detectado, iniciando captura");
                speech_buffer.start_speech();
                speech_started = true;
                let _ = event_tx.send(PipelineEvent::SpeechStarted);
            }
            VadEvent::SpeechEnded | VadEvent::MaxDurationReached => {
                if speech_started {
                    let duration_ms = speech_buffer.speech_duration_ms();
                    let _ = event_tx.send(PipelineEvent::SpeechEnded { duration_ms });
                    break;
                }
            }
            VadEvent::None => {
                // Agregar audio si estamos capturando speech
                if vad_state.is_capturing() && speech_started {
                    speech_buffer.push_speech(&resampled);

                    // Verificar limite de duracion
                    if speech_buffer.is_at_capacity() {
                        vad_state.force_end();
                        let duration_ms = speech_buffer.speech_duration_ms();
                        let _ = event_tx.send(PipelineEvent::SpeechEnded { duration_ms });
                        break;
                    }
                }
            }
        }
    }

    // Detener captura
    capture.stop();

    // Verificar si hay speech suficiente
    if !speech_buffer.has_speech() {
        log::info!("No se detecto speech suficiente");
        return Ok(CaptureResult::NoSpeech);
    }

    // Obtener audio acumulado
    let speech_audio = speech_buffer.end_speech();
    let audio_duration_s = speech_audio.len() as f32 / 16000.0;

    log::info!(
        "Speech capturado: {} samples ({:.2}s)",
        speech_audio.len(),
        audio_duration_s
    );

    Ok(CaptureResult::Success {
        audio: speech_audio,
        duration_s: audio_duration_s,
    })
}

/// Ejecuta el pipeline de grabacion completo
async fn run_recording_pipeline(
    config_arc: Arc<std::sync::Mutex<PipelineConfig>>,
    state: Arc<std::sync::Mutex<RecordingState>>,
    cancel_flag: Arc<AtomicBool>,
    event_tx: mpsc::UnboundedSender<PipelineEvent>,
    transcriber_arc: Arc<TokioMutex<Option<WhisperTranscriber>>>,
) -> anyhow::Result<()> {
    // Obtener configuracion
    let config = {
        let cfg = config_arc.lock().unwrap();
        cfg.clone()
    };

    let sound_enabled = config.app_config.sound_enabled;

    // Fase 1: Captura de audio (sincrona, en blocking task)
    let event_tx_capture = event_tx.clone();
    let cancel_flag_capture = cancel_flag.clone();
    
    let capture_result = tokio::task::spawn_blocking(move || {
        run_audio_capture(config, cancel_flag_capture, event_tx_capture)
    })
    .await
    .map_err(|e| anyhow::anyhow!("Error en task de captura: {}", e))??;

    // Procesar resultado de captura
    let (speech_audio, audio_duration_s) = match capture_result {
        CaptureResult::Success { audio, duration_s } => (audio, duration_s),
        CaptureResult::Cancelled => {
            *state.lock().unwrap() = RecordingState::Idle;
            let _ = event_tx.send(PipelineEvent::StateChanged(RecordingState::Idle));
            play_sound_if_enabled(SoundCue::Stop, sound_enabled);
            return Ok(());
        }
        CaptureResult::NoSpeech => {
            *state.lock().unwrap() = RecordingState::Idle;
            let _ = event_tx.send(PipelineEvent::StateChanged(RecordingState::Idle));
            play_sound_if_enabled(SoundCue::Stop, sound_enabled);
            return Ok(());
        }
    };

    // Cambiar a estado de procesamiento
    *state.lock().unwrap() = RecordingState::Processing;
    let _ = event_tx.send(PipelineEvent::StateChanged(RecordingState::Processing));
    play_sound_if_enabled(SoundCue::Stop, sound_enabled);

    // Fase 2: Transcribir con Whisper
    let transcribe_start = Instant::now();
    
    let text = {
        let transcriber_lock = transcriber_arc.lock().await;
        match transcriber_lock.as_ref() {
            Some(transcriber) => transcriber.transcribe(&speech_audio).await?,
            None => return Err(anyhow::anyhow!("Transcriber no disponible")),
        }
    };
    
    let processing_time_ms = transcribe_start.elapsed().as_millis() as u64;

    log::info!(
        "Transcripcion completada en {}ms: '{}'",
        processing_time_ms,
        text
    );

    let _ = event_tx.send(PipelineEvent::TranscriptionComplete {
        text: text.clone(),
        audio_duration_s,
        processing_time_ms,
    });

    // Fase 3: Copiar al clipboard si hay texto
    if !text.is_empty() {
        match ClipboardManager::new() {
            Ok(mut clipboard) => {
                if let Err(e) = clipboard.set_text(&text) {
                    log::error!("Error copiando al clipboard: {}", e);
                    let _ = event_tx.send(PipelineEvent::Error {
                        message: format!("Error copiando al clipboard: {}", e),
                    });
                    play_sound_if_enabled(SoundCue::Error, sound_enabled);
                } else {
                    let _ = event_tx.send(PipelineEvent::CopiedToClipboard { text });
                    play_sound_if_enabled(SoundCue::Success, sound_enabled);
                }
            }
            Err(e) => {
                log::error!("Error inicializando clipboard: {}", e);
                let _ = event_tx.send(PipelineEvent::Error {
                    message: format!("Error con clipboard: {}", e),
                });
                play_sound_if_enabled(SoundCue::Error, sound_enabled);
            }
        }
    } else {
        log::info!("Transcripcion vacia, no se copia al clipboard");
        play_sound_if_enabled(SoundCue::Stop, sound_enabled);
    }

    // Volver a idle
    *state.lock().unwrap() = RecordingState::Idle;
    let _ = event_tx.send(PipelineEvent::StateChanged(RecordingState::Idle));

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pipeline_config_default() {
        let config = PipelineConfig::default();
        assert_eq!(config.max_recording_duration_s, 30.0);
        assert_eq!(config.app_config.language, "es");
    }

    #[test]
    fn test_pipeline_creation() {
        let config = PipelineConfig::default();
        let mut pipeline = Pipeline::new(config);
        
        assert_eq!(pipeline.state(), RecordingState::Idle);
        assert!(pipeline.take_event_receiver().is_some());
        assert!(pipeline.take_event_receiver().is_none()); // Solo una vez
    }
}
